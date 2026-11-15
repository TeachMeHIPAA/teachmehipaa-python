"""The request pipeline: Organization binding, auth, idempotency, retries and
error mapping. The sync and async pipelines differ only in how they wait;
everything they build or read comes from `_request` and `_retry`."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable

import httpx
from pydantic import TypeAdapter

from ._auth import AsyncTokenProvider, TokenProvider
from ._config import ClientConfig
from ._errors import error_from_response
from ._files import read_uploads
from ._models import BinaryResponse
from ._pagination import AsyncPage, ItemT, PageBody, PaginationStyle, SyncPage
from ._request import (
    INTROSPECTION,
    ApiRequest,
    ModelT,
    T,
    bearer_token,
    build_request,
    read_binary,
    read_model,
    read_organization_id,
    read_union,
    read_write_result,
)
from ._retry import AsyncSender, Replay, RetryPolicy, SyncSender


def _retry_policy(config: ClientConfig, api_request: ApiRequest) -> RetryPolicy:
    # An Idempotency-Key deliberately plays no part: the API ignores keys on
    # PATCH and DELETE, so a caller's key must not make them retryable.
    return RetryPolicy(
        retry_safe=api_request.retry_safe,
        max_retries=api_request.max_retries(config),
    )


def _replay(
    api_request: ApiRequest, invalidate: Callable[[str], None]
) -> Replay | None:
    # A public endpoint's 401 can't be fixed by a fresh token.
    if not api_request.authenticated:
        return None
    return lambda refused: invalidate(bearer_token(refused))


class SyncPipeline:
    def __init__(
        self,
        config: ClientConfig,
        sender: SyncSender,
        token_provider: TokenProvider,
    ) -> None:
        self.config = config
        self._sender = sender
        # The client's injected sleep, for helpers that poll.
        self.sleep = sender.sleep
        self._tokens = token_provider
        self._organization_id = config.organization_id
        self._organization_lock = threading.Lock()

    def request(self, api_request: ApiRequest, model: type[ModelT]) -> ModelT:
        return read_model(self.send(api_request), model)

    def request_union(self, api_request: ApiRequest, adapter: TypeAdapter[T]) -> T:
        return read_union(self.send(api_request), adapter)

    def request_write_result(
        self, api_request: ApiRequest, model: type[ModelT]
    ) -> ModelT:
        return read_write_result(self.send(api_request), model)

    def request_page(
        self,
        api_request: ApiRequest,
        page_model: type[PageBody[ItemT]],
        *,
        cursor_param: str,
        style: PaginationStyle,
    ) -> SyncPage[ItemT]:
        body = read_model(self.send(api_request), page_model)
        return SyncPage(
            body,
            pipeline=self,
            request=api_request,
            cursor_param=cursor_param,
            style=style,
        )

    def request_empty(self, api_request: ApiRequest) -> None:
        self.send(api_request)

    def request_binary(self, api_request: ApiRequest) -> BinaryResponse:
        return read_binary(self.send(api_request))

    def send(self, api_request: ApiRequest) -> httpx.Response:
        organization_id = self._organization() if api_request.org_scoped else None
        return self._send(read_uploads(api_request), organization_id)

    def _send(
        self, api_request: ApiRequest, organization_id: str | None
    ) -> httpx.Response:
        idempotency_key = api_request.idempotency_key()
        return self._sender.send(
            lambda: build_request(
                self.config,
                api_request,
                access_token=(
                    self._tokens.access_token() if api_request.authenticated else None
                ),
                organization_id=organization_id,
                idempotency_key=idempotency_key,
            ),
            error_from_response,
            _retry_policy(self.config, api_request),
            replay=_replay(api_request, self._tokens.invalidate),
        )

    def _organization(self) -> str:
        with self._organization_lock:
            if self._organization_id is None:
                self._organization_id = read_organization_id(
                    self._send(INTROSPECTION, None)
                )
            return self._organization_id


class AsyncPipeline:
    def __init__(
        self,
        config: ClientConfig,
        sender: AsyncSender,
        token_provider: AsyncTokenProvider,
    ) -> None:
        self.config = config
        self._sender = sender
        # The client's injected sleep, for helpers that poll.
        self.sleep = sender.sleep
        self._tokens = token_provider
        self._organization_id = config.organization_id
        self._organization_lock = asyncio.Lock()

    async def request(self, api_request: ApiRequest, model: type[ModelT]) -> ModelT:
        return read_model(await self.send(api_request), model)

    async def request_union(
        self, api_request: ApiRequest, adapter: TypeAdapter[T]
    ) -> T:
        return read_union(await self.send(api_request), adapter)

    async def request_write_result(
        self, api_request: ApiRequest, model: type[ModelT]
    ) -> ModelT:
        return read_write_result(await self.send(api_request), model)

    async def request_page(
        self,
        api_request: ApiRequest,
        page_model: type[PageBody[ItemT]],
        *,
        cursor_param: str,
        style: PaginationStyle,
    ) -> AsyncPage[ItemT]:
        body = read_model(await self.send(api_request), page_model)
        return AsyncPage(
            body,
            pipeline=self,
            request=api_request,
            cursor_param=cursor_param,
            style=style,
        )

    async def request_empty(self, api_request: ApiRequest) -> None:
        await self.send(api_request)

    async def request_binary(self, api_request: ApiRequest) -> BinaryResponse:
        return read_binary(await self.send(api_request))

    async def send(self, api_request: ApiRequest) -> httpx.Response:
        organization_id = await self._organization() if api_request.org_scoped else None
        return await self._send(read_uploads(api_request), organization_id)

    async def _send(
        self, api_request: ApiRequest, organization_id: str | None
    ) -> httpx.Response:
        idempotency_key = api_request.idempotency_key()

        async def make_request() -> httpx.Request:
            return build_request(
                self.config,
                api_request,
                access_token=(
                    await self._tokens.access_token()
                    if api_request.authenticated
                    else None
                ),
                organization_id=organization_id,
                idempotency_key=idempotency_key,
            )

        return await self._sender.send(
            make_request,
            error_from_response,
            _retry_policy(self.config, api_request),
            replay=_replay(api_request, self._tokens.invalidate),
        )

    async def _organization(self) -> str:
        async with self._organization_lock:
            if self._organization_id is None:
                self._organization_id = read_organization_id(
                    await self._send(INTROSPECTION, None)
                )
            return self._organization_id
