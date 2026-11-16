from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Sequence
from types import TracebackType
from typing import ClassVar, TypeVar

import httpx

from ._core._auth import (
    AsyncClientCredentialsTokenProvider,
    AsyncTokenProvider,
    ClientCredentials,
    ClientCredentialsTokenProvider,
    TokenProvider,
)
from ._core._config import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    AppInfo,
    ClientConfig,
    Environment,
    make_config,
)
from ._core._pipeline import AsyncPipeline, SyncPipeline
from ._core._retry import AsyncSender, SyncSender
from ._webhooks import Webhook
from .resources._root import AsyncResources, SyncResources

ProviderT = TypeVar("ProviderT", TokenProvider, AsyncTokenProvider)


def _credentials_or_provider(
    client_id: str | None,
    client_secret: str | None,
    token_provider: ProviderT | None,
    scopes: Sequence[str] | None,
) -> ClientCredentials | ProviderT | None:
    """The credentials to mint with, the provider that supplies every Access
    token instead, or `None` for a client that makes only public calls."""
    if client_id is None and client_secret is None and scopes is None:
        # Without a token provider either, this is a public client; half a
        # pair of client credentials is a mistake, so it still fails below.
        return token_provider
    if token_provider is None:
        if client_id is None or client_secret is None:
            raise TypeError("pass client_id and client_secret, or token_provider")
        return ClientCredentials(client_id, client_secret)
    conflicting = [
        name
        for name, value in (
            ("client_id", client_id),
            ("client_secret", client_secret),
            ("scopes", scopes),
        )
        if value is not None
    ]
    if conflicting:
        raise TypeError(
            "give either token_provider or client_id and client_secret, not both "
            f"(got {', '.join(conflicting)} too; scopes belong to the token "
            "provider)"
        )
    return token_provider


class _ConfigView:
    """Read-only access to the client's configuration, which is fixed at
    construction (ADR-0002)."""

    _config: ClientConfig

    @property
    def environment(self) -> Environment:
        return self._config.environment

    @property
    def base_url(self) -> str:
        return self._config.base_url

    @property
    def max_retries(self) -> int:
        return self._config.max_retries

    @property
    def timeout(self) -> httpx.Timeout:
        return self._config.timeout


class TeachMeHipaa(_ConfigView, SyncResources):
    """A client for one Organization's view of the TeachMeHIPAA Developer API.

    Pass the API client's id and secret; the client mints, caches and renews
    Access tokens itself and discovers the Organization the credential is
    bound to unless `organization_id` is given. Or pass a `token_provider`,
    such as a `StaticTokenProvider`, to supply every Access token from
    elsewhere.

    With neither, the client makes only public calls (`courses`,
    `certificate_verifications.retrieve`); any other call raises
    `ValueError` before sending anything.
    """

    webhooks: ClassVar[type[Webhook]] = Webhook
    """Delivery verification. A class attribute: it needs only the Signing
    secret, so it works without credentials or a request."""

    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        token_provider: TokenProvider | None = None,
        environment: Environment = "live",
        base_url: str | None = None,
        organization_id: str | None = None,
        scopes: Sequence[str] | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        http_client: httpx.Client | None = None,
        app_info: AppInfo | None = None,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        auth = _credentials_or_provider(
            client_id, client_secret, token_provider, scopes
        )
        self._config = make_config(
            environment=environment,
            base_url=base_url,
            organization_id=organization_id,
            scopes=scopes,
            max_retries=max_retries,
            timeout=timeout,
            app_info=app_info,
            clock=clock,
        )
        self._http_client = http_client or httpx.Client(timeout=self._config.timeout)
        sender = SyncSender(self._http_client, sleep or time.sleep)
        tokens = (
            ClientCredentialsTokenProvider(auth, self._config, sender)
            if isinstance(auth, ClientCredentials)
            else auth
        )
        super().__init__(SyncPipeline(self._config, sender, tokens))

    def close(self) -> None:
        """Close the underlying httpx client, including one passed in."""
        self._http_client.close()

    def __enter__(self) -> TeachMeHipaa:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


class AsyncTeachMeHipaa(_ConfigView, AsyncResources):
    """The asyncio twin of `TeachMeHipaa`, with the same surface."""

    webhooks: ClassVar[type[Webhook]] = Webhook
    """Delivery verification. A class attribute: it needs only the Signing
    secret, so it works without credentials or a request."""

    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        token_provider: AsyncTokenProvider | None = None,
        environment: Environment = "live",
        base_url: str | None = None,
        organization_id: str | None = None,
        scopes: Sequence[str] | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        http_client: httpx.AsyncClient | None = None,
        app_info: AppInfo | None = None,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        auth = _credentials_or_provider(
            client_id, client_secret, token_provider, scopes
        )
        self._config = make_config(
            environment=environment,
            base_url=base_url,
            organization_id=organization_id,
            scopes=scopes,
            max_retries=max_retries,
            timeout=timeout,
            app_info=app_info,
            clock=clock,
        )
        self._http_client = http_client or httpx.AsyncClient(
            timeout=self._config.timeout
        )
        sender = AsyncSender(self._http_client, sleep or asyncio.sleep)
        tokens = (
            AsyncClientCredentialsTokenProvider(auth, self._config, sender)
            if isinstance(auth, ClientCredentials)
            else auth
        )
        super().__init__(AsyncPipeline(self._config, sender, tokens))

    async def close(self) -> None:
        """Close the underlying httpx client, including one passed in."""
        await self._http_client.aclose()

    async def __aenter__(self) -> AsyncTeachMeHipaa:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()
