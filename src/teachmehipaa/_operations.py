"""Operations (grilling Q24): work that may finish after the request that
started it, with `wait()` to poll until it is done.

The sync and async Operations differ only in how they wait; the backoff,
the outcome checks and the export decoding are shared.
"""

from __future__ import annotations

import base64
import random
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, Generic, Literal, TypeAlias

import pydantic
from typing_extensions import TypeVar

from ._core._errors import FieldError, TeachMeHipaaError, problem_message
from ._core._models import BaseModel
from ._core._request import ApiRequest, RequestOptions
from ._core._sentinel import NOT_GIVEN, NotGiven
from ._core._unions import UNKNOWN_VARIANT, by_property
from .types._models import Operation as OperationModel

if TYPE_CHECKING:
    from ._core._pipeline import AsyncPipeline, SyncPipeline

DEFAULT_TIMEOUT = 300.0
DEFAULT_INTERVAL = 1.0
MAX_INTERVAL = 10.0

ResponseT = TypeVar("ResponseT", default=Any)

_OPERATION_NAME = re.compile(r"organizations/[^/]+/operations/([^/]+)")


def operation_id_from_name(name: str) -> str:
    """The `operation_id` in an Operation's `name`, which is
    `organizations/{orgId}/operations/{operationId}`: what
    `operations.retrieve` takes."""
    match = _OPERATION_NAME.fullmatch(name)
    if match is None:
        raise ValueError(
            f"{name!r} is not an Operation name "
            "(organizations/{orgId}/operations/{operationId})"
        )
    return match.group(1)


def poll_delay(interval: float, poll_number: int) -> float:
    """Seconds to wait before poll `poll_number` (from 1).

    The ceiling doubles from `interval` up to 10 s, and jitter picks 50-100 %
    of it so that many waiters don't poll in step. Nothing waits less than
    `interval`, and an `interval` longer than the cap stays as it is.
    """
    ceiling = min(interval * 2.0 ** (poll_number - 1), max(MAX_INTERVAL, interval))
    # Jitter spreads waiters out; it is not security.
    return max(interval, ceiling * (0.5 + random.random() / 2))  # noqa: S311


def _retrieval(name: str, request_id: str | NotGiven) -> ApiRequest:
    # The same call as the generated `operations.retrieve`.
    return ApiRequest(
        "GET",
        "/organizations/{orgId}/operations/{operationId}",
        path_params={"operationId": operation_id_from_name(name)},
        org_scoped=True,
        retry_safe=True,
        options=RequestOptions(request_id=request_id),
    )


class WebhookDeliverySent(BaseModel):
    """The endpoint accepted the Delivery."""

    tag: Literal["sent"] = pydantic.Field(alias="_tag")
    response_status: int
    """The endpoint's HTTP status."""


class WebhookDeliveryFailed(BaseModel):
    """Delivery stopped for good; `reason` says why."""

    tag: Literal["failed"] = pydantic.Field(alias="_tag")
    reason: str
    response_status: int | None = None
    """The endpoint's last status, when it answered at all."""


class WebhookDeliverySettled(BaseModel):
    """The Delivery had already ended before this Operation; `status` says
    how."""

    tag: Literal["settled"] = pydantic.Field(alias="_tag")
    status: str


class UnknownWebhookDeliveryResult(BaseModel):
    """A `WebhookDeliveryResult` of a kind this version of the library
    doesn't know. Its other fields are kept in `model_extra`."""

    tag: str = pydantic.Field(alias="_tag")


# The spec leaves these Operations' `response` untyped; the webhook worker
# settles them with one of these.
WebhookDeliveryResult: TypeAlias = Annotated[
    Annotated[WebhookDeliverySent, pydantic.Tag("sent")]
    | Annotated[WebhookDeliveryFailed, pydantic.Tag("failed")]
    | Annotated[WebhookDeliverySettled, pydantic.Tag("settled")]
    | Annotated[UnknownWebhookDeliveryResult, pydantic.Tag(UNKNOWN_VARIANT)],
    pydantic.Discriminator(
        by_property("_tag", "tag", frozenset({"sent", "failed", "settled"}))
    ),
]
"""How a Test delivery or a redrive ended: the `response` of the Operation
that `webhook_subscriptions.test` and `.redrive` return. Tell the variants
apart by `tag`; others may appear, so handle tags you don't recognize."""


@dataclass(frozen=True)
class ExportResult:
    """The file an export Operation produced: `enrollments.export`,
    `certificates.export` or `learners.export`."""

    csv: str
    """The whole CSV file as text: RFC 4180, CRLF line endings."""
    filename: str | None
    """A suggested file name, such as `enrollments-org_acme.csv`."""
    row_count: int | None
    """The number of data rows, not counting the header."""


class _OperationBase(OperationModel, Generic[ResponseT]):
    response: ResponseT | None = None
    """The result, once `done` is `true`."""

    def export_result(self) -> ExportResult:
        """The CSV file of a done export Operation.

        Raises:
            OperationFailedError: The export failed.
            ValueError: The Operation is not done, or is not an export.
        """
        return _export_result(self)


class Operation(_OperationBase[ResponseT], Generic[ResponseT]):
    """An Operation returned by `TeachMeHipaa`.

    `response` holds the result once `done` is true, unless `error` holds
    the problem. Most Operations are done when they are returned; Test
    deliveries and redrives finish later, so call `wait()`.
    """

    _pipeline: SyncPipeline | None = pydantic.PrivateAttr(default=None)

    def wait(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        interval: float = DEFAULT_INTERVAL,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> Operation[ResponseT]:
        """Poll until the Operation is done and return its final state.

        An Operation that is already done returns at once, without a request.
        Polls back off from `interval` seconds to 10 s; the last one lands on
        the `timeout`, in seconds. `request_id` is sent as `x-request-id` on
        every poll.

        Raises:
            OperationFailedError: The Operation finished with an error.
            OperationTimeoutError: It was not done within `timeout`.
        """
        if self.done:
            return _settled(self)
        pipeline = _bound(self._pipeline, self)
        clock = pipeline.config.clock
        deadline = clock() + timeout
        latest = self
        poll_number = 1
        while True:
            remaining = deadline - clock()
            if remaining <= 0:
                raise _timed_out(latest, timeout)
            delay = poll_delay(interval, poll_number)
            pipeline.sleep(min(delay, remaining))
            latest = request_operation(
                pipeline, _retrieval(self.name, request_id), type(self)
            )
            if latest.done:
                return _settled(latest)
            if delay >= remaining:
                raise _timed_out(latest, timeout)
            poll_number += 1


class AsyncOperation(_OperationBase[ResponseT], Generic[ResponseT]):
    """The asyncio twin of `Operation`, returned by `AsyncTeachMeHipaa`."""

    _pipeline: AsyncPipeline | None = pydantic.PrivateAttr(default=None)

    async def wait(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        interval: float = DEFAULT_INTERVAL,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> AsyncOperation[ResponseT]:
        """Poll until the Operation is done and return its final state.

        An Operation that is already done returns at once, without a request.
        Polls back off from `interval` seconds to 10 s; the last one lands on
        the `timeout`, in seconds. Cancelling the task stops waiting.
        `request_id` is sent as `x-request-id` on every poll.

        Raises:
            OperationFailedError: The Operation finished with an error.
            OperationTimeoutError: It was not done within `timeout`.
        """
        if self.done:
            return _settled(self)
        pipeline = _bound(self._pipeline, self)
        clock = pipeline.config.clock
        deadline = clock() + timeout
        latest = self
        poll_number = 1
        while True:
            remaining = deadline - clock()
            if remaining <= 0:
                raise _timed_out(latest, timeout)
            delay = poll_delay(interval, poll_number)
            await pipeline.sleep(min(delay, remaining))
            latest = await async_request_operation(
                pipeline, _retrieval(self.name, request_id), type(self)
            )
            if latest.done:
                return _settled(latest)
            if delay >= remaining:
                raise _timed_out(latest, timeout)
            poll_number += 1


class OperationFailedError(TeachMeHipaaError):
    """An Operation finished with an error. The problem's fields are on the
    error, and `operation` is the failed Operation."""

    def __init__(
        self,
        message: str,
        *,
        operation: _OperationBase[Any],
        **fields: Any,
    ) -> None:
        super().__init__(message, **fields)
        self.operation = operation


class OperationTimeoutError(TeachMeHipaaError):
    """An Operation was not done within `wait()`'s timeout. `operation` is
    the last state seen; it may still finish, so it can be waited on again."""

    def __init__(
        self, message: str, *, operation: Operation[Any] | AsyncOperation[Any]
    ) -> None:
        super().__init__(
            message,
            request_id=operation.last_response.request_id,
            headers=operation.last_response.headers,
        )
        self.operation = operation


PipelineT = TypeVar("PipelineT")
OperationT = TypeVar("OperationT", bound="_OperationBase[Any]")


def _bound(pipeline: PipelineT | None, operation: _OperationBase[Any]) -> PipelineT:
    if pipeline is None:
        raise RuntimeError(
            f"Operation {operation.name} was not returned by an API call, so it "
            "has no client to poll with"
        )
    return pipeline


def _settled(operation: OperationT) -> OperationT:
    """The finished Operation, or the error it finished with."""
    problem = operation.error
    if problem is None:
        return operation
    raise OperationFailedError(
        problem_message(
            problem.detail,
            problem.title,
            problem.code,
            f"Operation {operation.name} failed",
        ),
        operation=operation,
        status=problem.status,
        code=problem.code,
        title=problem.title,
        detail=problem.detail,
        errors=tuple(
            FieldError(path=item.path, message=item.message)
            for item in problem.errors or ()
        ),
        request_id=operation.last_response.request_id,
        headers=operation.last_response.headers,
    )


def _export_result(operation: _OperationBase[Any]) -> ExportResult:
    if not operation.done:
        raise ValueError(f"Operation {operation.name} is not done; call wait() first")
    # The spec says only that an export's `response` "holds the CSV file". The
    # API sends it inline as the monorepo's `ExportArtifact`:
    # `{format: "csv", contentType, filename, rowCount, dataBase64}`.
    artifact = _settled(operation).response
    if (
        not isinstance(artifact, dict)
        or artifact.get("format") != "csv"
        or not isinstance(artifact.get("dataBase64"), str)
    ):
        raise ValueError(f"Operation {operation.name} did not produce a CSV export")
    filename = artifact.get("filename")
    row_count = artifact.get("rowCount")
    return ExportResult(
        csv=base64.b64decode(artifact["dataBase64"], validate=True).decode(),
        filename=filename if isinstance(filename, str) else None,
        row_count=row_count if isinstance(row_count, int) else None,
    )


def _timed_out(
    operation: Operation[Any] | AsyncOperation[Any], timeout: float
) -> OperationTimeoutError:
    return OperationTimeoutError(
        f"Operation {operation.name} was not done after {timeout:g} s",
        operation=operation,
    )


SyncOperationT = TypeVar("SyncOperationT", bound=Operation)
AsyncOperationT = TypeVar("AsyncOperationT", bound=AsyncOperation)


def request_operation(
    pipeline: SyncPipeline,
    api_request: ApiRequest,
    operation_type: type[SyncOperationT],
) -> SyncOperationT:
    """Send a request whose success is an Operation, bound to the pipeline
    that `wait()` polls through."""
    operation = pipeline.request(api_request, operation_type)
    operation._pipeline = pipeline
    return operation


async def async_request_operation(
    pipeline: AsyncPipeline,
    api_request: ApiRequest,
    operation_type: type[AsyncOperationT],
) -> AsyncOperationT:
    operation = await pipeline.request(api_request, operation_type)
    operation._pipeline = pipeline
    return operation
