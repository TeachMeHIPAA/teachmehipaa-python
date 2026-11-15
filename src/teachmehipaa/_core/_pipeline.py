"""The request pipeline: Organization binding, auth and sending. The sync and
async pipelines differ only in how they wait; everything they build or read
comes from `_request`."""

from __future__ import annotations

import asyncio
import threading

import httpx

from ._auth import AsyncTokenProvider, TokenProvider
from ._config import ClientConfig
from ._request import (
    INTROSPECTION,
    ApiRequest,
    ModelT,
    build_request,
    read_model,
    read_organization_id,
)


class SyncPipeline:
    def __init__(
        self,
        config: ClientConfig,
        http_client: httpx.Client,
        token_provider: TokenProvider,
    ) -> None:
        self.config = config
        self.http_client = http_client
        self._tokens = token_provider
        self._organization_id = config.organization_id
        self._organization_lock = threading.Lock()

    def request(self, api_request: ApiRequest, model: type[ModelT]) -> ModelT:
        organization_id = self._organization() if api_request.org_scoped else None
        request = build_request(
            self.config,
            api_request,
            access_token=self._tokens.access_token(),
            organization_id=organization_id,
        )
        return read_model(self.http_client.send(request), model)

    def _organization(self) -> str:
        with self._organization_lock:
            if self._organization_id is None:
                request = build_request(
                    self.config, INTROSPECTION, access_token=self._tokens.access_token()
                )
                self._organization_id = read_organization_id(
                    self.http_client.send(request)
                )
            return self._organization_id


class AsyncPipeline:
    def __init__(
        self,
        config: ClientConfig,
        http_client: httpx.AsyncClient,
        token_provider: AsyncTokenProvider,
    ) -> None:
        self.config = config
        self.http_client = http_client
        self._tokens = token_provider
        self._organization_id = config.organization_id
        self._organization_lock = asyncio.Lock()

    async def request(self, api_request: ApiRequest, model: type[ModelT]) -> ModelT:
        organization_id = await self._organization() if api_request.org_scoped else None
        request = build_request(
            self.config,
            api_request,
            access_token=await self._tokens.access_token(),
            organization_id=organization_id,
        )
        return read_model(await self.http_client.send(request), model)

    async def _organization(self) -> str:
        async with self._organization_lock:
            if self._organization_id is None:
                request = build_request(
                    self.config,
                    INTROSPECTION,
                    access_token=await self._tokens.access_token(),
                )
                self._organization_id = read_organization_id(
                    await self.http_client.send(request)
                )
            return self._organization_id
