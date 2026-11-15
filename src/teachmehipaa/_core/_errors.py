"""The error hierarchy (grilling Q20) and the mapping from HTTP responses and
transport failures onto it.

Names avoid Python's builtins: `PermissionDeniedError` rather than
`PermissionError` and `APIConnectionError` rather than `ConnectionError`, so
`from teachmehipaa import *` or a partner's `except PermissionError:` around
file I/O never silently changes meaning.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

import httpx


@dataclass(frozen=True)
class FieldError:
    """One invalid field from a problem's `errors` list. `path` is the
    dot-joined field path, or the header name (such as `Idempotency-Key`)."""

    path: str
    message: str


class TeachMeHipaaError(Exception):
    """Base class for every error the library raises.

    Fields mirror the API's RFC 9457 problem body. `code` is an open string:
    new codes are added to the API over time. `body` is the raw response text.
    Errors raised without a response leave the response fields empty.
    """

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str | None = None,
        title: str | None = None,
        detail: str | None = None,
        errors: tuple[FieldError, ...] = (),
        request_id: str | None = None,
        headers: httpx.Headers | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self.errors = errors
        self.request_id = request_id
        self.headers = headers if headers is not None else httpx.Headers()
        self.body = body

    def __str__(self) -> str:
        if self.request_id is None:
            return self.message
        return f"{self.message} (request id: {self.request_id})"


class AuthenticationError(TeachMeHipaaError):
    """401: the Access token is missing, expired or revoked."""


class PermissionDeniedError(TeachMeHipaaError):
    """403: the token lacks a Scope, or the Organization refuses the action."""


class NotFoundError(TeachMeHipaaError):
    """404: no such object in the bound Organization."""


class ConflictError(TeachMeHipaaError):
    """409: the object's state forbids the action, or an identical request
    is still in flight (`code == "conflict"`)."""


class PreconditionFailedError(TeachMeHipaaError):
    """412 for a stale `If-Match`, 428 for a missing one."""


class InvalidRequestError(TeachMeHipaaError):
    """400, 405, 406, 415 or 422: the request itself is wrong."""


class IdempotencyError(InvalidRequestError):
    """422 `idempotency_key_reuse`: the key was used with a different body."""


class RateLimitError(TeachMeHipaaError):
    """429: too many requests."""

    @property
    def retry_after(self) -> float | None:
        """Seconds the API asked the caller to wait, from `Retry-After`."""
        return parse_retry_after(self.headers)


class APIError(TeachMeHipaaError):
    """5xx, or a response the API should never send, such as an HTML page
    where JSON was expected."""


class OAuthError(TeachMeHipaaError):
    """The token endpoint refused a grant. `code` is the OAuth `error` and
    `detail` its `error_description`."""


WebhookSignatureErrorCode: TypeAlias = Literal[
    "missing_header",
    "invalid_timestamp",
    "timestamp_outside_tolerance",
    "body_hash_mismatch",
    "signature_mismatch",
]


class WebhookSignatureError(TeachMeHipaaError):
    """A webhook Delivery failed verification. `code` says which check
    failed.

    Never carries the Delivery's body or headers: a Delivery holds Learner
    data, and errors end up in logs and error trackers (ADR-0007).
    """

    code: WebhookSignatureErrorCode

    def __init__(self, code: WebhookSignatureErrorCode, message: str) -> None:
        super().__init__(message, code=code)


class APIConnectionError(TeachMeHipaaError):
    """No response arrived: DNS, connect, TLS or a dropped connection."""


class APITimeoutError(APIConnectionError):
    """No response arrived within the timeout."""


_STATUS_ERRORS: Mapping[int, type[TeachMeHipaaError]] = {
    400: InvalidRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    405: InvalidRequestError,
    406: InvalidRequestError,
    409: ConflictError,
    412: PreconditionFailedError,
    415: InvalidRequestError,
    422: InvalidRequestError,
    428: PreconditionFailedError,
    429: RateLimitError,
}


def error_from_response(response: httpx.Response) -> TeachMeHipaaError:
    """Map an API response onto the hierarchy by status, then by `code`."""
    problem = _json_object(response)
    if problem is None:
        return unexpected_response_error(response)
    code = _str_or_none(problem.get("code"))
    error_class = _STATUS_ERRORS.get(response.status_code, APIError)
    if error_class is InvalidRequestError and code == "idempotency_key_reuse":
        error_class = IdempotencyError
    title = _str_or_none(problem.get("title"))
    detail = _str_or_none(problem.get("detail"))
    return error_class(
        detail or title or code or f"HTTP {response.status_code}",
        status=response.status_code,
        code=code,
        title=title,
        detail=detail,
        errors=_field_errors(problem.get("errors")),
        **_response_fields(response),
    )


def oauth_error_from_response(response: httpx.Response) -> TeachMeHipaaError:
    """Map a token endpoint response, which uses the OAuth error shape
    `{error, error_description}` rather than a problem."""
    body = _json_object(response)
    oauth_code = None if body is None else _str_or_none(body.get("error"))
    if body is None or oauth_code is None:
        return error_from_response(response)
    detail = _str_or_none(body.get("error_description"))
    return OAuthError(
        detail or oauth_code,
        status=response.status_code,
        code=oauth_code,
        detail=detail,
        **_response_fields(response),
    )


def unexpected_response_error(response: httpx.Response) -> APIError:
    content_type = response.headers.get("content-type") or "no content type"
    return APIError(
        f"The API answered HTTP {response.status_code} with {content_type} "
        "instead of JSON. Check that base_url points at the TeachMeHIPAA API.",
        status=response.status_code,
        **_response_fields(response),
    )


def connection_error(exc: httpx.TransportError) -> APIConnectionError:
    error: APIConnectionError
    if isinstance(exc, httpx.TimeoutException):
        error = APITimeoutError("The request to the TeachMeHIPAA API timed out.")
    else:
        error = APIConnectionError(f"Could not reach the TeachMeHIPAA API: {exc}")
    error.__cause__ = exc
    return error


def is_json(response: httpx.Response) -> bool:
    content_type: str = response.headers.get("content-type", "")
    media_type = content_type.split(";")[0].strip()
    return media_type == "application/json" or media_type.endswith("+json")


def parse_retry_after(headers: httpx.Headers) -> float | None:
    # The API only sends delta-seconds; an HTTP-date would need a wall clock
    # the library deliberately doesn't read, so it falls back to backoff.
    try:
        seconds = float(headers.get("retry-after", ""))
    except ValueError:
        return None
    return seconds if seconds >= 0 else None


def _response_fields(response: httpx.Response) -> dict[str, Any]:
    return {
        "request_id": response.headers.get("x-request-id"),
        "headers": response.headers,
        "body": response.text,
    }


def _json_object(response: httpx.Response) -> dict[str, Any] | None:
    if not is_json(response):
        return None
    try:
        body = response.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


def _field_errors(value: object) -> tuple[FieldError, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        FieldError(path=str(item.get("path", "")), message=str(item.get("message", "")))
        for item in value
        if isinstance(item, dict)
    )


def _str_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None
