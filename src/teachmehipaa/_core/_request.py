"""Pure request building and response reading, shared by the sync and async
pipelines. Nothing here performs I/O."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TypeVar
from urllib.parse import quote

import httpx

from ._config import ClientConfig
from ._errors import TeachMeHipaaError, error_from_response
from ._models import BaseModel, LastResponse
from ._sentinel import NotGiven

Primitive = str | int | float | bool | None
ModelT = TypeVar("ModelT", bound=BaseModel)

_PATH_PARAM = re.compile(r"\{(\w+)\}")


@dataclass(frozen=True)
class ApiRequest:
    """One API call as a resource method describes it.

    `path` is the spec's path template, such as
    `/organizations/{orgId}/learners/{learnerId}`. `{orgId}` is filled from
    the client's Organization binding, never by the caller (ADR-0003).
    """

    method: str
    path: str
    path_params: Mapping[str, str] = field(default_factory=dict)
    query: Mapping[str, Primitive | NotGiven] = field(default_factory=dict)

    @property
    def org_scoped(self) -> bool:
        return "{orgId}" in self.path


INTROSPECTION = ApiRequest("GET", "/auth/introspection")


def build_request(
    config: ClientConfig,
    api_request: ApiRequest,
    *,
    access_token: str,
    organization_id: str | None = None,
) -> httpx.Request:
    path_params = dict(api_request.path_params)
    if organization_id is not None:
        path_params["orgId"] = organization_id
    query = {
        name: value
        for name, value in api_request.query.items()
        if not isinstance(value, NotGiven)
    }
    return httpx.Request(
        api_request.method,
        config.base_url + _expand_path(api_request.path, path_params),
        params=query,
        headers={
            "accept": "application/json",
            "user-agent": config.user_agent,
            "authorization": f"Bearer {access_token}",
        },
        extensions={"timeout": config.timeout.as_dict()},
    )


def _expand_path(template: str, params: Mapping[str, str]) -> str:
    # Only ids are escaped, so a custom method's literal `:verb` suffix
    # survives.
    return _PATH_PARAM.sub(lambda match: quote(params[match[1]], safe=""), template)


def read_model(response: httpx.Response, model: type[ModelT]) -> ModelT:
    if response.is_error:
        raise error_from_response(response)
    parsed = model.model_validate(response.json())
    parsed._last_response = LastResponse(response.status_code, response.headers)
    return parsed


def read_organization_id(response: httpx.Response) -> str:
    if response.is_error:
        raise error_from_response(response)
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
