"""The request pipeline: Organization binding, auth, idempotency, retries and
error mapping. The sync and async pipelines differ only in how they wait;
everything they build or read comes from `_request` and `_retry`."""

from __future__ import annotations

import asyncio
import threading

import httpx

from ._auth import AsyncTokenProvider, TokenProvider
from ._config import ClientConfig
from ._errors import error_from_response
from ._request import (
    INTROSPECTION,
    ApiRequest,
    ModelT,
    bearer_token,
    build_request,
    read_model,
    read_organization_id,
)
from ._retry import AsyncSender, RetryPolicy, SyncSender


def _retry_policy(
    config: ClientConfig, api_request: ApiRequest, idempotency_key: str | None
) -> RetryPolicy:
    return RetryPolicy(
        retry_safe=api_request.retry_safe or idempotency_key is not None,
        max_retries=api_request.max_retries(config),
    )


class SyncPipeline:
    def __init__(
        self,
        config: ClientConfig,
        sender: SyncSender,
        token_provider: TokenProvider,
    ) -> None:
        self.config = config
        self._sender = sender
        self._tokens = token_provider
        self._organization_id = config.organization_id
        self._organization_lock = threading.Lock()

    def request(self, api_request: ApiRequest, model: type[ModelT]) -> ModelT:
        organization_id = self._organization() if api_request.org_scoped else None
        return read_model(self._send(api_request, organization_id), model)

    def _send(
        self, api_request: ApiRequest, organization_id: str | None
    ) -> httpx.Response:
        idempotency_key = api_request.idempotency_key()
        return self._sender.send(
            lambda: build_request(
                self.config,
                api_request,
                access_token=self._tokens.access_token(),
                organization_id=organization_id,
                idempotency_key=idempotency_key,
            ),
            error_from_response,
            _retry_policy(self.config, api_request, idempotency_key),
            replay=lambda refused: self._tokens.invalidate(bearer_token(refused)),
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
        self._tokens = token_provider
        self._organization_id = config.organization_id
        self._organization_lock = asyncio.Lock()

    async def request(self, api_request: ApiRequest, model: type[ModelT]) -> ModelT:
        organization_id = await self._organization() if api_request.org_scoped else None
        return read_model(await self._send(api_request, organization_id), model)

    async def _send(
        self, api_request: ApiRequest, organization_id: str | None
    ) -> httpx.Response:
        idempotency_key = api_request.idempotency_key()

        async def make_request() -> httpx.Request:
            return build_request(
                self.config,
                api_request,
                access_token=await self._tokens.access_token(),
                organization_id=organization_id,
                idempotency_key=idempotency_key,
            )

        return await self._sender.send(
            make_request,
            error_from_response,
            _retry_policy(self.config, api_request, idempotency_key),
            replay=lambda refused: self._tokens.invalidate(bearer_token(refused)),
        )

    async def _organization(self) -> str:
        async with self._organization_lock:
            if self._organization_id is None:
                self._organization_id = read_organization_id(
                    await self._send(INTROSPECTION, None)
                )
            return self._organization_id
