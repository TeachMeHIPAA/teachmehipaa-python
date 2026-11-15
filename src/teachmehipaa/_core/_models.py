from __future__ import annotations

from dataclasses import dataclass

import httpx
import pydantic
from pydantic.alias_generators import to_camel


@dataclass(frozen=True)
class LastResponse:
    """The HTTP response a returned object was read from."""

    status: int
    headers: httpx.Headers

    @property
    def request_id(self) -> str | None:
        request_id: str | None = self.headers.get("x-request-id")
        return request_id

    @property
    def etag(self) -> str | None:
        etag: str | None = self.headers.get("etag")
        return etag


class BaseModel(pydantic.BaseModel):
    """Base for response models.

    Unknown fields are kept (ADR-0006): `/v1` grows by adding fields, and a
    strict model would break every partner on each additive release.
    """

    model_config = pydantic.ConfigDict(extra="allow", alias_generator=to_camel)

    _last_response: LastResponse | None = pydantic.PrivateAttr(default=None)

    @property
    def last_response(self) -> LastResponse:
        if self._last_response is None:
            raise RuntimeError(
                f"this {type(self).__name__} was not returned by an API call"
            )
        return self._last_response
