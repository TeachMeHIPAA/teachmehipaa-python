"""The request pipeline: Organization binding, auth, idempotency, retries and
error mapping. The sync and async pipelines differ only in how they wait;
everything they build or read comes from `_request` and `_retry`."""

from __future__ import annotations

import asyncio
import threading

import httpx
from pydantic import TypeAdapter

from ._auth import AsyncTokenProvider, TokenProvider
from ._config import ClientConfig
from ._errors import error_from_response, unexpected_response_error
from ._files import read_uploads
from ._models import AsyncBinaryStream, BinaryResponse, BinaryStream, NotModified
from ._pagination import AsyncPage, ItemT, PageBody, SyncPage
from ._request import (
    INTROSPECTION,
    ApiRequest,
    ModelT,
    T,
    bearer_token,
    build_request,
    filename_of,
    is_expected_file,
    read_binary,
    read_conditional,
    read_model,
    read_organization_id,
    read_union,
    read_write_result,
)
from ._retry import AsyncReplay, AsyncSender, Replay, RetryPolicy, SyncSender


def _retry_policy(config: ClientConfig, api_request: ApiRequest) -> RetryPolicy:
    # An Idempotency-Key deliberately plays no part: the API ignores keys on
    # PATCH and DELETE, so a caller's key must not make them retryable.
    return RetryPolicy(
        retry_safe=api_request.retry_safe,
        max_retries=api_request.max_retries(config),
    )


def _replay(api_request: ApiRequest, tokens: TokenProvider) -> Replay | None:
    # A public endpoint's 401 can't be fixed by a fresh token.
    if not api_request.authenticated:
        return None

    def replay(refused: httpx.Request) -> bool:
        refused_token = bearer_token(refused)
        tokens.invalidate(refused_token)
        # A provider that can't renew (a static token) hands back the same
        # token, which the API would only refuse again.
        return tokens.access_token() != refused_token

    return replay


def _async_replay(
    api_request: ApiRequest, tokens: AsyncTokenProvider
) -> AsyncReplay | None:
    if not api_request.authenticated:
        return None

    async def replay(refused: httpx.Request) -> bool:
        refused_token = bearer_token(refused)
        tokens.invalidate(refused_token)
        return await tokens.access_token() != refused_token

    return replay


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

    def request_conditional(
        self, api_request: ApiRequest, model: type[ModelT]
    ) -> ModelT | NotModified:
        return read_conditional(
            self.send(api_request), model, conditional=api_request.conditional_read
        )

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
        position_field: str | None = None,
    ) -> SyncPage[ItemT]:
        body = read_model(self.send(api_request), page_model)
        return SyncPage(
            body,
            pipeline=self,
            request=api_request,
            cursor_param=cursor_param,
            position_field=position_field,
        )

    def request_empty(self, api_request: ApiRequest) -> None:
        self.send(api_request)

    def request_binary(self, api_request: ApiRequest) -> BinaryResponse:
        return read_binary(self.send(api_request), api_request)

    def request_binary_stream(self, api_request: ApiRequest) -> BinaryStream:
        response = self.send(api_request, stream=True)
        if not is_expected_file(response, api_request):
            try:
                response.read()
            finally:
                response.close()
            raise unexpected_response_error(response)
        return BinaryStream(
            response,
            content_type=response.headers.get("content-type"),
            filename=filename_of(response),
        )

    def send(self, api_request: ApiRequest, *, stream: bool = False) -> httpx.Response:
        api_request = read_uploads(api_request)
        organization_id = self._organization() if api_request.org_scoped else None
        return self._send(api_request, organization_id, stream=stream)

    def _send(
        self,
        api_request: ApiRequest,
        organization_id: str | None,
        *,
        stream: bool = False,
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
            replay=_replay(api_request, self._tokens),
            stream=stream,
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

    async def request_conditional(
        self, api_request: ApiRequest, model: type[ModelT]
    ) -> ModelT | NotModified:
        return read_conditional(
            await self.send(api_request),
            model,
            conditional=api_request.conditional_read,
        )

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
        position_field: str | None = None,
    ) -> AsyncPage[ItemT]:
        body = read_model(await self.send(api_request), page_model)
        return AsyncPage(
            body,
            pipeline=self,
            request=api_request,
            cursor_param=cursor_param,
            position_field=position_field,
        )

    async def request_empty(self, api_request: ApiRequest) -> None:
        await self.send(api_request)

    async def request_binary(self, api_request: ApiRequest) -> BinaryResponse:
        return read_binary(await self.send(api_request), api_request)

    async def request_binary_stream(self, api_request: ApiRequest) -> AsyncBinaryStream:
        response = await self.send(api_request, stream=True)
        if not is_expected_file(response, api_request):
            try:
                await response.aread()
            finally:
                await response.aclose()
            raise unexpected_response_error(response)
        return AsyncBinaryStream(
            response,
            content_type=response.headers.get("content-type"),
            filename=filename_of(response),
        )

    async def send(
        self, api_request: ApiRequest, *, stream: bool = False
    ) -> httpx.Response:
        if api_request.binary_parts:
            # Reading a file blocks; keep it off the event loop.
            api_request = await asyncio.to_thread(read_uploads, api_request)
        organization_id = await self._organization() if api_request.org_scoped else None
        return await self._send(api_request, organization_id, stream=stream)

    async def _send(
        self,
        api_request: ApiRequest,
        organization_id: str | None,
        *,
        stream: bool = False,
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
            replay=_async_replay(api_request, self._tokens),
            stream=stream,
        )

    async def _organization(self) -> str:
        async with self._organization_lock:
            if self._organization_id is None:
                self._organization_id = read_organization_id(
                    await self._send(INTROSPECTION, None)
                )
            return self._organization_id
