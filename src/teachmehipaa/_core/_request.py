"""Pure request building and response reading, shared by the sync and async
pipelines. Nothing here performs I/O."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TypeVar
from urllib.parse import quote

import httpx

from ._config import ClientConfig
from ._errors import (
    TeachMeHipaaError,
    error_from_response,
    is_json,
    unexpected_response_error,
)
from ._models import BaseModel, LastResponse
from ._sentinel import NOT_GIVEN, NotGiven

Primitive = str | int | float | bool | None
ModelT = TypeVar("ModelT", bound=BaseModel)

_PATH_PARAM = re.compile(r"\{(\w+)\}")


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
    `/organizations/{orgId}/learners/{learnerId}`. `{orgId}` is filled from
    the client's Organization binding, never by the caller (ADR-0003).

    `retry_safe` and `idempotency_key_required` come from the IR. A request
    that carries an `Idempotency-Key` is retry-safe whatever the flag says.
    Top-level `body` fields that are `NOT_GIVEN` are left out.
    """

    method: str
    path: str
    path_params: Mapping[str, str] = field(default_factory=dict)
    query: Mapping[str, Primitive | NotGiven] = field(default_factory=dict)
    headers: Mapping[str, str] = field(default_factory=dict)
    body: Mapping[str, object] | None = None
    content_type: str = "application/json"
    retry_safe: bool = False
    idempotency_key_required: bool = False
    options: RequestOptions = field(default_factory=RequestOptions)

    @property
    def org_scoped(self) -> bool:
        return "{orgId}" in self.path

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
    access_token: str,
    organization_id: str | None = None,
    idempotency_key: str | None = None,
) -> httpx.Request:
    path_params = dict(api_request.path_params)
    if organization_id is not None:
        path_params["orgId"] = organization_id
    query = {
        name: value
        for name, value in api_request.query.items()
        if not isinstance(value, NotGiven)
    }
    headers = {
        "accept": "application/json",
        "user-agent": config.user_agent,
        "authorization": f"Bearer {access_token}",
        **api_request.headers,
    }
    if idempotency_key is not None:
        headers["idempotency-key"] = idempotency_key
    content = None
    if api_request.body is not None:
        headers["content-type"] = api_request.content_type
        content = json.dumps(
            {
                name: value
                for name, value in api_request.body.items()
                if not isinstance(value, NotGiven)
            }
        ).encode()
    return httpx.Request(
        api_request.method,
        config.base_url + _expand_path(api_request.path, path_params),
        params=query,
        headers=headers,
        content=content,
        extensions={"timeout": api_request.timeout(config).as_dict()},
    )


def bearer_token(request: httpx.Request) -> str:
    return request.headers["authorization"].removeprefix("Bearer ")


def _expand_path(template: str, params: Mapping[str, str]) -> str:
    # Only ids are escaped, so a custom method's literal `:verb` suffix
    # survives.
    return _PATH_PARAM.sub(lambda match: quote(params[match[1]], safe=""), template)


def read_model(response: httpx.Response, model: type[ModelT]) -> ModelT:
    if response.is_error:
        raise error_from_response(response)
    # Unknown paths answer 200 text/html (a Nuxt page), so check before
    # parsing.
    if not is_json(response):
        raise unexpected_response_error(response)
    parsed = model.model_validate(response.json())
    parsed._last_response = LastResponse(response.status_code, response.headers)
    return parsed


def read_organization_id(response: httpx.Response) -> str:
    if response.is_error:
        raise error_from_response(response)
    if not is_json(response):
        raise unexpected_response_error(response)
    organization_id = response.json().get("orgId")
    if not isinstance(organization_id, str):
        raise TeachMeHipaaError(
            "The access token is not bound to an Organization. Partner-level "
            "tokens cannot call Organization endpoints.",
            status=response.status_code,
            request_id=response.headers.get("x-request-id"),
            headers=response.headers,
        )
    return organization_id
