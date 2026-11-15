"""Pure request building and response reading, shared by the sync and async
pipelines. Nothing here performs I/O."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypeVar
from urllib.parse import quote

import httpx
from pydantic import TypeAdapter

from ._config import ClientConfig
from ._errors import (
    TeachMeHipaaError,
    error_from_response,
    is_json,
    unexpected_response_error,
)
from ._files import Upload
from ._models import BaseModel, BinaryResponse, LastResponse
from ._sentinel import NOT_GIVEN, NotGiven

QueryValue = str | int | float | bool | datetime | None
ModelT = TypeVar("ModelT", bound=BaseModel)
T = TypeVar("T")

_PATH_PARAM = re.compile(r"\{(\w+)\}")
_FILENAME = re.compile(r'filename="?([^";]+)"?')


@dataclass(frozen=True)
class RequestOptions:
    """Per-call overrides of the client's settings."""

    max_retries: int | NotGiven = NOT_GIVEN
    timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN
    idempotency_key: str | NotGiven = NOT_GIVEN

    def __post_init__(self) -> None:
        if not isinstance(self.max_retries, NotGiven) and self.max_retries < 0:
            raise ValueError("max_retries must be zero or more")


@dataclass(frozen=True)
class ApiRequest:
    """One API call as a resource method describes it.

    `path` is the spec's path template, such as
    `/organizations/{orgId}/learners/{learnerId}`. For an `org_scoped` call,
    `{orgId}` is filled from the client's Organization binding, never by the
    caller (ADR-0003).

    `retry_safe` and `idempotency_key_required` come from the IR. Only
    `retry_safe` decides whether a call is retried: the API ignores an
    `Idempotency-Key` on PATCH and DELETE, so a key doesn't make them safe.

    Top-level `body` fields and `query` and `headers` values that are
    `NOT_GIVEN` are left out. Nested body values are mappings with
    snake_case keys, sent in camelCase. For `multipart/form-data`,
    `binary_parts` names the file fields and their content types; the
    pipeline reads those files into `Upload`s before sending. Every other
    field is sent as a JSON part.
    """

    method: str
    path: str
    path_params: Mapping[str, str] = field(default_factory=dict)
    query: Mapping[str, QueryValue | NotGiven] = field(default_factory=dict)
    headers: Mapping[str, str | NotGiven] = field(default_factory=dict)
    body: Mapping[str, object] | None = None
    content_type: str = "application/json"
    binary_parts: Mapping[str, str] = field(default_factory=dict)
    org_scoped: bool = False
    authenticated: bool = True
    retry_safe: bool = False
    idempotency_key_required: bool = False
    options: RequestOptions = field(default_factory=RequestOptions)

    def max_retries(self, config: ClientConfig) -> int:
        if isinstance(self.options.max_retries, NotGiven):
            return config.max_retries
        return self.options.max_retries

    def timeout(self, config: ClientConfig) -> httpx.Timeout:
        if isinstance(self.options.timeout, NotGiven):
            return config.timeout
        return httpx.Timeout(self.options.timeout)

    def idempotency_key(self) -> str | None:
        """The key for one call. The pipeline asks once per call, not per
        attempt, so every retry replays under the same key."""
        if not isinstance(self.options.idempotency_key, NotGiven):
            return self.options.idempotency_key
        return str(uuid.uuid4()) if self.idempotency_key_required else None


INTROSPECTION = ApiRequest("GET", "/auth/introspection", retry_safe=True)


def build_request(
    config: ClientConfig,
    api_request: ApiRequest,
    *,
    access_token: str | None,
    organization_id: str | None = None,
    idempotency_key: str | None = None,
) -> httpx.Request:
    path_params = dict(api_request.path_params)
    if organization_id is not None:
        path_params["orgId"] = organization_id
    query = {
        name: _query_value(value)
        for name, value in api_request.query.items()
        if not isinstance(value, NotGiven)
    }
    headers = {
        "accept": "application/json",
        "user-agent": config.user_agent,
        **_given(api_request.headers),
    }
    if access_token is not None:
        headers["authorization"] = f"Bearer {access_token}"
    if idempotency_key is not None:
        headers["idempotency-key"] = idempotency_key
    content = None
    files = None
    if api_request.body is not None:
        body = _given(api_request.body)
        if api_request.content_type == "multipart/form-data":
            # httpx sets the content type itself, with the part boundary.
            files = _multipart(body, api_request.binary_parts)
        else:
            headers["content-type"] = api_request.content_type
            content = _json_bytes({name: wire_value(v) for name, v in body.items()})
    return httpx.Request(
        api_request.method,
        config.base_url + _expand_path(api_request.path, path_params),
        params=query,
        headers=headers,
        content=content,
        files=files,
        extensions={"timeout": api_request.timeout(config).as_dict()},
    )


def bearer_token(request: httpx.Request) -> str:
    return request.headers["authorization"].removeprefix("Bearer ")


def camel(name: str) -> str:
    """The wire name of a snake_case request key."""
    first, *rest = name.split("_")
    return first + "".join(part[:1].upper() + part[1:] for part in rest)


def wire_value(value: object) -> object:
    """A request value as JSON-ready data: nested mapping keys in camelCase,
    datetimes in ISO 8601."""
    if isinstance(value, Mapping):
        return {camel(key): wire_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [wire_value(item) for item in value]
    if isinstance(value, datetime):
        return _iso8601(value)
    return value


def with_fixed(
    value: Mapping[str, object] | NotGiven, fixed: Mapping[str, object]
) -> Mapping[str, object]:
    """`value` with the fields a method pins (grilling Q25) set."""
    return {**({} if isinstance(value, NotGiven) else value), **fixed}


def _given(values: Mapping[str, T | NotGiven]) -> dict[str, T]:
    return {
        name: value for name, value in values.items() if not isinstance(value, NotGiven)
    }


def _query_value(value: QueryValue) -> str | int | float | bool | None:
    return _iso8601(value) if isinstance(value, datetime) else value


def _iso8601(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _json_bytes(value: object) -> bytes:
    return json.dumps(value).encode()


def _multipart(
    body: Mapping[str, object], binary_parts: Mapping[str, str]
) -> dict[str, tuple[str | None, bytes, str]]:
    parts: dict[str, tuple[str | None, bytes, str]] = {}
    for name, value in body.items():
        content_type = binary_parts.get(name)
        if isinstance(value, Upload) and content_type is not None:
            parts[name] = (value.filename, value.content, content_type)
        else:
            parts[name] = (None, _json_bytes(wire_value(value)), "application/json")
    return parts


def _expand_path(template: str, params: Mapping[str, str]) -> str:
    # Only ids are escaped, so a custom method's literal `:verb` suffix
    # survives.
    return _PATH_PARAM.sub(lambda match: quote(params[match[1]], safe=""), template)


def _checked(response: httpx.Response) -> httpx.Response:
    if response.is_error:
        raise error_from_response(response)
    # Unknown paths answer 200 text/html (a Nuxt page), so check before
    # parsing.
    if not is_json(response):
        raise unexpected_response_error(response)
    return response


def _with_last_response(parsed: T, response: httpx.Response) -> T:
    if isinstance(parsed, BaseModel):
        parsed._last_response = LastResponse(response.status_code, response.headers)
    return parsed


def read_model(response: httpx.Response, model: type[ModelT]) -> ModelT:
    parsed = model.model_validate(_checked(response).json())
    return _with_last_response(parsed, response)


def read_union(response: httpx.Response, adapter: TypeAdapter[T]) -> T:
    parsed = adapter.validate_python(_checked(response).json())
    return _with_last_response(parsed, response)


def read_write_result(response: httpx.Response, model: type[ModelT]) -> ModelT:
    """A Learner write result: the API answers 201 when the write created
    the Learner and 200 when it already existed (grilling Q25)."""
    body = _checked(response).json()
    parsed = model.model_validate({**body, "created": response.status_code == 201})
    return _with_last_response(parsed, response)


def read_binary(response: httpx.Response) -> BinaryResponse:
    if response.is_error:
        raise error_from_response(response)
    disposition = response.headers.get("content-disposition", "")
    filename = _FILENAME.search(disposition)
    return BinaryResponse(
        content=response.content,
        content_type=response.headers.get("content-type"),
        filename=None if filename is None else filename[1],
        last_response=LastResponse(response.status_code, response.headers),
    )


def read_organization_id(response: httpx.Response) -> str:
    organization_id = _checked(response).json().get("orgId")
    if not isinstance(organization_id, str):
        raise TeachMeHipaaError(
            "The access token is not bound to an Organization. Partner-level "
            "tokens cannot call Organization endpoints.",
            status=response.status_code,
            request_id=response.headers.get("x-request-id"),
            headers=response.headers,
        )
    return organization_id
