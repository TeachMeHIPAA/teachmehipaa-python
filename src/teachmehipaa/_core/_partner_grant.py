"""Access tokens for one Grant, from its rotating Refresh token (ADR-0004)."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Sequence
from typing import Protocol

import httpx

from ._auth import AccessToken, ClientCredentials, require_text
from ._config import DEFAULT_TIMEOUT, AppInfo, Environment, make_token_endpoint
from ._errors import TokenStoreError
from ._grant_exchange import (
    ExchangeGuidance,
    GrantExchange,
    async_exchange_grant,
    exchange_grant,
)


class TokenStore(Protocol):
    """Where a Grant's Refresh token lives between processes, such as a
    database row or a secrets manager.

    Every exchange replaces the Refresh token, and presenting a replaced one
    revokes the Grant, so `save` must persist durably before it returns.
    """

    def load(self) -> str:
        """The Grant's current Refresh token, read once at the first
        exchange."""
        ...

    def save(self, refresh_token: str) -> None:
        """Persist the Refresh token that replaces the current one."""
        ...


class AsyncTokenStore(Protocol):
    """The asyncio twin of `TokenStore`."""

    async def load(self) -> str:
        """The Grant's current Refresh token, read once at the first
        exchange."""
        ...

    async def save(self, refresh_token: str) -> None:
        """Persist the Refresh token that replaces the current one."""
        ...


_REFRESH_GUIDANCE = ExchangeGuidance(
    network_failure=(
        "The Refresh token exchange was not retried, because replaying a "
        "Refresh token the endpoint may already have rotated revokes the "
        "Grant. If the next call fails with invalid_grant, re-run consent for "
        "this Organization."
    ),
    invalid_grant=(
        "The Grant was revoked, or its Refresh token was reused (presenting a "
        "superseded Refresh token revokes the Grant). Re-run consent for "
        "the Organization."
    ),
)

_LOAD_EMPTY = "token_store.load() returned no Refresh token."


class _GrantState:
    """What the sync and async providers share: credentials, the latest
    Refresh token and the cached Access token."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str | None,
        scopes: Sequence[str] | None,
        environment: Environment,
        base_url: str | None,
        timeout: float | httpx.Timeout,
        app_info: AppInfo | None,
        clock: Callable[[], float] | None,
    ) -> None:
        self.credentials = ClientCredentials.checked(client_id, client_secret)
        self.endpoint = make_token_endpoint(
            environment=environment,
            base_url=base_url,
            timeout=timeout,
            app_info=app_info,
            clock=clock,
        )
        self.scope = " ".join(scopes) if scopes else None
        self.latest_refresh_token = (
            None
            if refresh_token is None
            else require_text(refresh_token, "refresh_token")
        )
        self.token: AccessToken | None = None

    def cached(self) -> AccessToken | None:
        token = self.token
        if token is None or token.needs_refresh(self.endpoint.clock()):
            return None
        return token

    def refresh_form(self, refresh_token: str) -> dict[str, str]:
        if not isinstance(refresh_token, str) or not refresh_token:
            raise TokenStoreError(_LOAD_EMPTY)
        form = {"grant_type": "refresh_token", "refresh_token": refresh_token}
        if self.scope is not None:
            form["scope"] = self.scope
        return form

    def rotated(self, grant: GrantExchange) -> None:
        # The token just presented is superseded whatever happens next, so
        # this process must never present it again, even if the save fails.
        self.latest_refresh_token = grant.tokens.refresh_token

    def invalidate(self, access_token: str) -> None:
        if self.token is not None and self.token.value == access_token:
            self.token = None


def _save_failed() -> TokenStoreError:
    # The store didn't record the rotation, so the next process would load
    # and replay the superseded token and revoke the Grant. Using the new
    # Access token would hide that until it's too late, so raise instead.
    return TokenStoreError(
        "token_store.save() failed, so the new Access token was not used. "
        "Until a save succeeds, your store holds a superseded Refresh token, "
        "and exchanging it would revoke the Grant."
    )


class PartnerGrantTokenProvider:
    """Access tokens for one Grant, from its Refresh token.

    Create one provider per Grant and share it between clients: its lock is
    what keeps two exchanges of the same Refresh token from racing. Each
    rotated Refresh token goes to `token_store` before its Access token is
    used, and an exchange is never retried (ADR-0004).

    Args:
        client_id: Your Partner app's id (`app_…`).
        client_secret: Your Partner app's secret (`tmh_as_…`).
        token_store: Receives every rotated Refresh token.
        refresh_token: The Refresh token for the first exchange, e.g. straight
            from `oauth.exchange_code`. When omitted, the first exchange loads
            it from `token_store`.
        scopes: Narrows the Access token to these Scopes; it can never widen
            them.
        environment: Which deployment the Partner app belongs to. A client
            given this provider must use the same Environment and base URL.
        base_url: Overrides the Environment's base URL.
        timeout: Seconds to wait for the token endpoint.
        app_info: Identifies your integration in the User-Agent.
        http_client: Sends exchanges; by default a short-lived one each time.
        clock: Supplies the current time, in seconds. For tests.
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        token_store: TokenStore,
        refresh_token: str | None = None,
        scopes: Sequence[str] | None = None,
        environment: Environment = "live",
        base_url: str | None = None,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        app_info: AppInfo | None = None,
        http_client: httpx.Client | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._state = _GrantState(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            scopes=scopes,
            environment=environment,
            base_url=base_url,
            timeout=timeout,
            app_info=app_info,
            clock=clock,
        )
        self._token_store = token_store
        self._http_client = http_client
        self._lock = threading.Lock()

    @property
    def base_url(self) -> str:
        """Where this provider exchanges Refresh tokens. A client given this
        provider must call the same base URL."""
        return self._state.endpoint.base_url

    def access_token(self) -> str:
        with self._lock:
            token = self._state.cached()
            if token is None:
                token = self._state.token = self._mint()
            return token.value

    def invalidate(self, access_token: str) -> None:
        with self._lock:
            self._state.invalidate(access_token)

    def _mint(self) -> AccessToken:
        state = self._state
        refresh_token = state.latest_refresh_token or self._token_store.load()
        grant = exchange_grant(
            self._http_client,
            state.endpoint,
            state.credentials,
            state.refresh_form(refresh_token),
            _REFRESH_GUIDANCE,
        )
        state.rotated(grant)
        try:
            self._token_store.save(grant.tokens.refresh_token)
        except Exception as exc:
            raise _save_failed() from exc
        return AccessToken(grant.tokens.access_token, grant.expires_at)


class AsyncPartnerGrantTokenProvider:
    """The asyncio twin of `PartnerGrantTokenProvider`, with an
    `AsyncTokenStore`."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        token_store: AsyncTokenStore,
        refresh_token: str | None = None,
        scopes: Sequence[str] | None = None,
        environment: Environment = "live",
        base_url: str | None = None,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        app_info: AppInfo | None = None,
        http_client: httpx.AsyncClient | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._state = _GrantState(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            scopes=scopes,
            environment=environment,
            base_url=base_url,
            timeout=timeout,
            app_info=app_info,
            clock=clock,
        )
        self._token_store = token_store
        self._http_client = http_client
        self._lock = asyncio.Lock()

    @property
    def base_url(self) -> str:
        """Where this provider exchanges Refresh tokens. A client given this
        provider must call the same base URL."""
        return self._state.endpoint.base_url

    async def access_token(self) -> str:
        async with self._lock:
            token = self._state.cached()
            if token is None:
                token = self._state.token = await self._mint()
            return token.value

    def invalidate(self, access_token: str) -> None:
        # No await between the check and the clear, so no lock is needed.
        self._state.invalidate(access_token)

    async def _mint(self) -> AccessToken:
        state = self._state
        refresh_token = state.latest_refresh_token or await self._token_store.load()
        grant = await async_exchange_grant(
            self._http_client,
            state.endpoint,
            state.credentials,
            state.refresh_form(refresh_token),
            _REFRESH_GUIDANCE,
        )
        state.rotated(grant)
        try:
            await self._token_store.save(grant.tokens.refresh_token)
        except Exception as exc:
            raise _save_failed() from exc
        return AccessToken(grant.tokens.access_token, grant.expires_at)
