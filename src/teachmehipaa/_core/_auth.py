"""Token providers: the seam between the request pipeline and however an
Access token is obtained. The client-credentials adapter is the default."""

from __future__ import annotations

import asyncio
import threading
from base64 import b64encode
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import quote_plus, urlencode

import httpx

from ._config import ClientConfig
from ._errors import error_from_response

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


class AsyncTokenProvider(Protocol):
    async def access_token(self) -> str: ...


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
    if response.is_error:
        raise error_from_response(response)
    body = response.json()
    return AccessToken(
        value=body["access_token"],
        expires_at=minted_at + float(body["expires_in"]),
    )


class ClientCredentialsTokenProvider:
    """Caches one Access token and mints a new one when it nears expiry.
    Concurrent callers share a single mint."""

    def __init__(
        self,
        credentials: ClientCredentials,
        config: ClientConfig,
        send: Callable[[httpx.Request], httpx.Response],
    ) -> None:
        self._credentials = credentials
        self._config = config
        self._send = send
        self._token: AccessToken | None = None
        self._lock = threading.Lock()

    def access_token(self) -> str:
        with self._lock:
            if self._token is None or self._token.needs_refresh(self._config.clock()):
                minted_at = self._config.clock()
                response = self._send(self._credentials.token_request(self._config))
                self._token = read_access_token(response, minted_at=minted_at)
            return self._token.value


class AsyncClientCredentialsTokenProvider:
    """The asyncio twin of `ClientCredentialsTokenProvider`."""

    def __init__(
        self,
        credentials: ClientCredentials,
        config: ClientConfig,
        send: Callable[[httpx.Request], Awaitable[httpx.Response]],
    ) -> None:
        self._credentials = credentials
        self._config = config
        self._send = send
        self._token: AccessToken | None = None
        self._lock = asyncio.Lock()

    async def access_token(self) -> str:
        async with self._lock:
            if self._token is None or self._token.needs_refresh(self._config.clock()):
                minted_at = self._config.clock()
                request = self._credentials.token_request(self._config)
                response = await self._send(request)
                self._token = read_access_token(response, minted_at=minted_at)
            return self._token.value
