"""Pure request building and response reading, shared by the sync and async
pipelines. Nothing here performs I/O."""

from __future__ import annotations

import contextlib
import json
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypeVar
from urllib.parse import quote, unquote

import httpx
from pydantic import TypeAdapter

from ._config import ClientConfig
from ._errors import (
    TeachMeHipaaError,
    is_json,
    unexpected_response_error,
)
from ._files import Upload
from ._models import (
    REQUEST_ID_HEADER,
    BaseModel,
    BinaryResponse,
    ETagSource,
    LastResponse,
    NotModified,
    request_id_of,
)
from ._sentinel import NOT_GIVEN, NotGiven

QueryValue = str | int | float | bool | datetime | None
ModelT = TypeVar("ModelT", bound=BaseModel)
T = TypeVar("T")

_PATH_PARAM = re.compile(r"\{(\w+)\}")
_FILENAME = re.compile(r'filename="?([^";]+)"?', re.IGNORECASE)
_ENCODED_FILENAME = re.compile(r"filename\*=UTF-8''([^;\s]+)", re.IGNORECASE)


@dataclass(frozen=True)
class RequestOptions:
    """Per-call overrides of the client's settings."""

    max_retries: int | NotGiven = NOT_GIVEN
    timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN
    idempotency_key: str | NotGiven = NOT_GIVEN
    request_id: str | NotGiven = NOT_GIVEN

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

    `if_match` and `if_none_match` are checked when the request is built, so
    an object without an ETag is refused before anything is sent. A call
    with `if_none_match` treats 304 as a success. `binary_content_type` is
    the file type a binary download answers with.
    """

    method: str
    path: str
    path_params: Mapping[str, str] = field(default_factory=dict)
    query: Mapping[str, QueryValue | NotGiven] = field(default_factory=dict)
    headers: Mapping[str, str | NotGiven] = field(default_factory=dict)
    body: Mapping[str, object] | None = None
    content_type: str = "application/json"
    binary_parts: Mapping[str, str] = field(default_factory=dict)
    if_match: ETagSource | NotGiven = NOT_GIVEN
    if_none_match: ETagSource | NotGiven = NOT_GIVEN
    binary_content_type: str | None = None
    org_scoped: bool = False
    authenticated: bool = True
    retry_safe: bool = False
    idempotency_key_required: bool = False
    options: RequestOptions = field(default_factory=RequestOptions)

    def __post_init__(self) -> None:
        self.conditional_headers()

    def conditional_headers(self) -> dict[str, str]:
        headers = {}
        if not isinstance(self.if_match, NotGiven):
            headers["if-match"] = _etag_of(self.if_match, "if_match")
        if not isinstance(self.if_none_match, NotGiven):
            headers["if-none-match"] = _etag_of(self.if_none_match, "if_none_match")
        return headers

    @property
    def conditional_read(self) -> bool:
        return not isinstance(self.if_none_match, NotGiven)

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
    accept = "application/json"
    if api_request.binary_content_type is not None:
        # Errors still arrive as problem+json, so a download accepts both.
        accept = f"{api_request.binary_content_type}, application/problem+json"
    headers = {
        "accept": accept,
        "user-agent": config.user_agent,
        **_omit_not_given(api_request.headers),
        **api_request.conditional_headers(),
    }
    if access_token is not None:
        headers["authorization"] = f"Bearer {access_token}"
    if idempotency_key is not None:
        headers["idempotency-key"] = idempotency_key
    if not isinstance(api_request.options.request_id, NotGiven):
        headers[REQUEST_ID_HEADER] = api_request.options.request_id
    content = None
    files = None
    if api_request.body is not None:
        body = _omit_not_given(api_request.body)
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


def _etag_of(source: ETagSource, argument: str) -> str:
    if isinstance(source, str):
        return source
    try:
        etag = source.last_response.etag
    except RuntimeError as exc:
        raise ValueError(f"{argument} was given an object with no ETag") from exc
    if etag is None:
        raise ValueError(
            f"{argument} was given a {type(source).__name__} whose response had "
            "no ETag; pass the ETag string instead"
        )
    return etag


def _omit_not_given(values: Mapping[str, T | NotGiven]) -> dict[str, T]:
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
    # Unknown paths answer 200 text/html (a Nuxt page), so check before
    # parsing.
    if not is_json(response):
        raise unexpected_response_error(response)
    return response


def _with_last_response(parsed: T, response: httpx.Response) -> T:
    if isinstance(parsed, BaseModel):
        parsed._last_response = LastResponse(response.status_code, response.headers)
    return parsed


def read_conditional(
    response: httpx.Response, model: type[ModelT], *, conditional: bool
) -> ModelT | NotModified:
    if conditional and response.status_code == 304:
        return NotModified(LastResponse(response.status_code, response.headers))
    return read_model(response, model)


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


def is_expected_file(response: httpx.Response, api_request: ApiRequest) -> bool:
    """Whether a success carries the file type the IR promises. Unknown
    paths answer 200 with an HTML page, which must not be handed back as a
    PDF."""
    content_type: str = response.headers.get("content-type", "")
    expected = api_request.binary_content_type or ""
    return content_type.split(";")[0].strip().lower() == expected.lower()


def filename_of(response: httpx.Response) -> str | None:
    # RFC 6266: prefer the UTF-8 `filename*`, else the plain `filename`.
    disposition = response.headers.get("content-disposition", "")
    encoded = _ENCODED_FILENAME.search(disposition)
    if encoded is not None:
        # Malformed percent-encoding falls back to the plain parameter.
        with contextlib.suppress(UnicodeDecodeError):
            return unquote(encoded[1], errors="strict")
    plain = _FILENAME.search(disposition)
    return None if plain is None else plain[1]


def read_binary(response: httpx.Response, api_request: ApiRequest) -> BinaryResponse:
    if not is_expected_file(response, api_request):
        raise unexpected_response_error(response)
    return BinaryResponse(
        content=response.content,
        content_type=response.headers.get("content-type"),
        filename=filename_of(response),
        last_response=LastResponse(response.status_code, response.headers),
    )


def read_organization_id(response: httpx.Response) -> str:
    organization_id = _checked(response).json().get("orgId")
    if not isinstance(organization_id, str):
        raise TeachMeHipaaError(
            "The Access token is not bound to an Organization. "
            "Pass organization_id when you create the client.",
            status=response.status_code,
            request_id=request_id_of(response.headers),
            headers=response.headers,
        )
    return organization_id
