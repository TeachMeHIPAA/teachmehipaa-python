from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from types import TracebackType
from typing import Literal, Protocol, TypeAlias

import httpx
import pydantic
from pydantic.alias_generators import to_camel

# Undeclared in the spec, but the API sends it on every response and echoes
# one a caller sends.
REQUEST_ID_HEADER = "x-request-id"


def request_id_of(headers: httpx.Headers) -> str | None:
    request_id: str | None = headers.get(REQUEST_ID_HEADER)
    return request_id


@dataclass(frozen=True)
class LastResponse:
    """The HTTP response a returned object was read from."""

    status: int
    headers: httpx.Headers

    @property
    def request_id(self) -> str | None:
        return request_id_of(self.headers)

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


@dataclass(frozen=True)
class BinaryResponse:
    """A file the API answered with, such as a Certificate PDF."""

    content: bytes
    content_type: str | None
    filename: str | None
    last_response: LastResponse


class BinaryStream:
    """A file the API is sending, read as it arrives: what
    `download_pdf(..., stream=True)` returns.

    Use it as a context manager, or call `close()`, so the connection goes
    back to the pool. Retries and the timeout cover getting the response
    started; a failure while reading surfaces from `iter_bytes()`.
    """

    def __init__(
        self,
        response: httpx.Response,
        *,
        content_type: str | None,
        filename: str | None,
    ) -> None:
        self._response = response
        self.content_type = content_type
        self.filename = filename
        self.last_response = LastResponse(response.status_code, response.headers)

    def iter_bytes(self, chunk_size: int | None = None) -> Iterator[bytes]:
        return self._response.iter_bytes(chunk_size)

    def read(self) -> bytes:
        return self._response.read()

    def close(self) -> None:
        self._response.close()

    def __enter__(self) -> BinaryStream:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


class AsyncBinaryStream:
    """The async client's `BinaryStream`: `async with await
    client.certificates.download_pdf(cert_id, stream=True) as pdf`."""

    def __init__(
        self,
        response: httpx.Response,
        *,
        content_type: str | None,
        filename: str | None,
    ) -> None:
        self._response = response
        self.content_type = content_type
        self.filename = filename
        self.last_response = LastResponse(response.status_code, response.headers)

    def aiter_bytes(self, chunk_size: int | None = None) -> AsyncIterator[bytes]:
        return self._response.aiter_bytes(chunk_size)

    async def aread(self) -> bytes:
        return await self._response.aread()

    async def aclose(self) -> None:
        await self._response.aclose()

    async def __aenter__(self) -> AsyncBinaryStream:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()


@dataclass(frozen=True)
class NotModified:
    """A conditional read's answer when the copy the caller holds is current
    (304). It is falsy, so `client.courses.retrieve(id, if_none_match=cached)
    or cached` gives the current object either way."""

    last_response: LastResponse

    def __bool__(self) -> Literal[False]:
        return False


class HasLastResponse(Protocol):
    @property
    def last_response(self) -> LastResponse: ...


ETagSource: TypeAlias = str | HasLastResponse
"""An ETag as the API sent it, or any object the library returned, whose
`last_response.etag` is then used."""
