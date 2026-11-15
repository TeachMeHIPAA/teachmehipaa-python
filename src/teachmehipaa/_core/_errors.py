from __future__ import annotations

from typing import Any

import httpx


class TeachMeHipaaError(Exception):
    """Base class for every error the library raises.

    Fields mirror the API's RFC 9457 problem body. `code` is an open string:
    new codes are added to the API over time.
    """

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str | None = None,
        title: str | None = None,
        detail: str | None = None,
        request_id: str | None = None,
        headers: httpx.Headers | None = None,
        body: object = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self.request_id = request_id
        self.headers = headers if headers is not None else httpx.Headers()
        self.body = body

    def __str__(self) -> str:
        if self.request_id is None:
            return self.message
        return f"{self.message} (request id: {self.request_id})"


def error_from_response(response: httpx.Response) -> TeachMeHipaaError:
    body = _json_body(response)
    fields: dict[str, Any] = body if isinstance(body, dict) else {}
    # The token endpoint answers with an OAuth body ({error,
    # error_description}) rather than a problem.
    code = _str_or_none(fields.get("code")) or _str_or_none(fields.get("error"))
    title = _str_or_none(fields.get("title"))
    detail = _str_or_none(fields.get("detail")) or _str_or_none(
        fields.get("error_description")
    )
    return TeachMeHipaaError(
        detail or title or code or f"HTTP {response.status_code}",
        status=response.status_code,
        code=code,
        title=title,
        detail=detail,
        request_id=response.headers.get("x-request-id"),
        headers=response.headers,
        body=body,
    )


def _json_body(response: httpx.Response) -> object:
    if "json" not in response.headers.get("content-type", ""):
        return response.text
    try:
        return response.json()
    except ValueError:
        return response.text


def _str_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None
