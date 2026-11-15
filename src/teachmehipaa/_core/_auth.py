"""Token providers: the seam between the request pipeline and however an
Access token is obtained. The client-credentials adapter is the default."""

from __future__ import annotations

import asyncio
import threading
from base64 import b64encode
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import quote_plus, urlencode

import httpx

from ._config import ClientConfig
from ._errors import is_json, oauth_error_from_response, unexpected_response_error
from ._retry import AsyncSender, RetryPolicy, SyncSender

# Re-mint this long before expiry so a token never lapses mid-request.
REFRESH_MARGIN_SECONDS = 60.0


@dataclass(frozen=True)
class AccessToken:
    value: str
    expires_at: float

    def needs_refresh(self, now: float) -> bool:
        return now >= self.expires_at - REFRESH_MARGIN_SECONDS


class TokenProvider(Protocol):
    def access_token(self) -> str: ...

    def invalidate(self, access_token: str) -> None:
        """Drop `access_token`, which the API refused, so the next
        `access_token()` mints afresh. A token minted since is kept."""


class AsyncTokenProvider(Protocol):
    async def access_token(self) -> str: ...

    def invalidate(self, access_token: str) -> None:
        """Drop `access_token`, which the API refused, so the next
        `access_token()` mints afresh. A token minted since is kept."""


@dataclass(frozen=True)
class ClientCredentials:
    client_id: str
    client_secret: str = field(repr=False)

    def token_request(self, config: ClientConfig) -> httpx.Request:
        # RFC 6749 §2.3.1: form-encode each half before base64.
        credentials = f"{quote_plus(self.client_id)}:{quote_plus(self.client_secret)}"
        form = {"grant_type": "client_credentials"}
        if config.scopes is not None:
            form["scope"] = " ".join(config.scopes)
        return httpx.Request(
            "POST",
            f"{config.base_url}/auth/token",
            content=urlencode(form).encode(),
            headers={
                "accept": "application/json",
                "authorization": f"Basic {b64encode(credentials.encode()).decode()}",
                "content-type": "application/x-www-form-urlencoded",
                "user-agent": config.user_agent,
            },
            extensions={"timeout": config.timeout.as_dict()},
        )


def read_access_token(response: httpx.Response, *, minted_at: float) -> AccessToken:
    if not is_json(response):
        raise unexpected_response_error(response)
    body = response.json()
    return AccessToken(
        value=body["access_token"],
        expires_at=minted_at + float(body["expires_in"]),
    )


def mint_retry_policy(config: ClientConfig) -> RetryPolicy:
    # A client-credentials grant mints a fresh token each time, so replaying
    # it is harmless. Refresh-token and authorization-code exchanges must
    # never use this: replaying one revokes the Grant (ADR-0004).
    return RetryPolicy(retry_safe=True, max_retries=config.max_retries)


class ClientCredentialsTokenProvider:
    """Caches one Access token and mints a new one when it nears expiry.
    Concurrent callers share a single mint."""

    def __init__(
        self,
        credentials: ClientCredentials,
        config: ClientConfig,
        sender: SyncSender,
    ) -> None:
        self._credentials = credentials
        self._config = config
        self._sender = sender
        self._token: AccessToken | None = None
        self._lock = threading.Lock()

    def access_token(self) -> str:
        with self._lock:
            if self._token is None or self._token.needs_refresh(self._config.clock()):
                minted_at = self._config.clock()
                response = self._sender.send(
                    lambda: self._credentials.token_request(self._config),
                    oauth_error_from_response,
                    mint_retry_policy(self._config),
                )
                self._token = read_access_token(response, minted_at=minted_at)
            return self._token.value

    def invalidate(self, access_token: str) -> None:
        with self._lock:
            if self._token is not None and self._token.value == access_token:
                self._token = None


class AsyncClientCredentialsTokenProvider:
    """The asyncio twin of `ClientCredentialsTokenProvider`."""

    def __init__(
        self,
        credentials: ClientCredentials,
        config: ClientConfig,
        sender: AsyncSender,
    ) -> None:
        self._credentials = credentials
        self._config = config
        self._sender = sender
        self._token: AccessToken | None = None
        self._lock = asyncio.Lock()

    async def access_token(self) -> str:
        async with self._lock:
            if self._token is None or self._token.needs_refresh(self._config.clock()):
                minted_at = self._config.clock()
                response = await self._sender.send(
                    self._token_request,
                    oauth_error_from_response,
                    mint_retry_policy(self._config),
                )
                self._token = read_access_token(response, minted_at=minted_at)
            return self._token.value

    def invalidate(self, access_token: str) -> None:
        # No await between the check and the clear, so no lock is needed.
        if self._token is not None and self._token.value == access_token:
            self._token = None

    async def _token_request(self) -> httpx.Request:
        return self._credentials.token_request(self._config)
