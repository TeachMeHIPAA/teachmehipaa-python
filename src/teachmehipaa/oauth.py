"""Helpers for connecting Organizations to a Partner app: PKCE pairs, the
consent URL and the code exchange. They need no client."""

from __future__ import annotations

import hashlib
import secrets
from base64 import urlsafe_b64encode
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal
from urllib.parse import quote, urlencode, urlsplit

import httpx

from ._core._auth import ClientCredentials
from ._core._config import DEFAULT_TIMEOUT, AppInfo, Environment, make_token_endpoint
from ._core._grant_exchange import (
    ExchangeGuidance,
    GrantTokens,
    async_exchange_grant,
    exchange_grant,
    require_text,
)

__all__ = [
    "GrantTokens",
    "PkcePair",
    "async_exchange_code",
    "authorize_url",
    "create_pkce_pair",
    "create_state",
    "exchange_code",
]

_CODE_EXCHANGE_GUIDANCE = ExchangeGuidance(
    connection=(
        "The code exchange was not retried: the code may have been consumed, "
        "and a code works only once. Re-run consent to get a new code."
    )
)

# The Sandbox console's consent URL is not published yet, so Sandbox callers
# pass `authorization_url` rather than the library guessing a host.
_AUTHORIZATION_URLS: Mapping[Environment, str | None] = MappingProxyType(
    {
        "live": "https://console.teachmehipaa.com/oauth/authorize",
        "sandbox": None,
    }
)


@dataclass(frozen=True)
class PkcePair:
    """A PKCE code verifier and the challenge to put on the consent URL."""

    code_verifier: str
    """Keep this server-side until the code exchange; never send it to the
    browser."""
    code_challenge: str
    method: Literal["S256"] = "S256"
    """The only method TeachMeHIPAA accepts."""


def _base64url(data: bytes) -> str:
    return urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _random_token() -> str:
    # 32 bytes encode to 43 base64url characters: the shortest verifier
    # RFC 7636 allows, carrying the full 256 bits it recommends.
    return secrets.token_urlsafe(32)


def create_pkce_pair() -> PkcePair:
    """A fresh code verifier and its S256 code challenge."""
    code_verifier = _random_token()
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return PkcePair(code_verifier=code_verifier, code_challenge=_base64url(digest))


def create_state() -> str:
    """A random `state` that binds the consent redirect to the admin's
    session."""
    return _random_token()


def _consent_base_url(environment: Environment, authorization_url: str | None) -> str:
    if authorization_url is not None:
        parts = urlsplit(authorization_url)
        if not parts.scheme or not parts.netloc:
            raise ValueError("authorization_url must be an absolute URL")
        return authorization_url
    if environment not in _AUTHORIZATION_URLS:
        raise ValueError(
            f"environment must be 'live' or 'sandbox', not {environment!r}"
        )
    url = _AUTHORIZATION_URLS[environment]
    if url is None:
        raise ValueError(
            f"pass authorization_url: the {environment} consent URL is not built in"
        )
    return url


def authorize_url(
    *,
    client_id: str,
    redirect_uri: str,
    scopes: Sequence[str],
    state: str,
    code_challenge: str,
    environment: Environment = "live",
    authorization_url: str | None = None,
) -> str:
    """The URL to send an Organization admin to, to grant your Partner app
    access.

    Args:
        client_id: Your Partner app's id (`app_…`).
        redirect_uri: One of the app's registered redirect URIs, matched
            exactly.
        scopes: The Scopes to ask the admin for.
        state: Echoed back on the redirect. Check it matches before
            exchanging the code; `create_state()` makes one.
        code_challenge: From `create_pkce_pair()`.
        environment: Which deployment's console to use. Sandbox has no
            built-in consent URL, so it needs `authorization_url`.
        authorization_url: Overrides the Environment's consent URL.
    """
    base = urlsplit(_consent_base_url(environment, authorization_url))
    query = urlencode(
        {
            "response_type": "code",
            "client_id": require_text(client_id, "client_id"),
            "redirect_uri": require_text(redirect_uri, "redirect_uri"),
            "scope": " ".join(scopes),
            # Without state, a forged redirect could attach an attacker's
            # Grant to the partner's session (RFC 6749 §10.12).
            "state": require_text(state, "state"),
            "code_challenge": require_text(code_challenge, "code_challenge"),
            "code_challenge_method": "S256",
        },
        # `quote` writes spaces as %20; form encoding's `+` is only read back
        # as a space by form parsers.
        quote_via=quote,
    )
    return base._replace(query=query).geturl()


def _code_exchange_form(
    *, code: str, redirect_uri: str, code_verifier: str
) -> dict[str, str]:
    return {
        "grant_type": "authorization_code",
        "code": require_text(code, "code"),
        "redirect_uri": require_text(redirect_uri, "redirect_uri"),
        "code_verifier": require_text(code_verifier, "code_verifier"),
    }


def _partner_app(client_id: str, client_secret: str) -> ClientCredentials:
    return ClientCredentials(
        require_text(client_id, "client_id"),
        require_text(client_secret, "client_secret"),
    )


def exchange_code(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    code_verifier: str,
    environment: Environment = "live",
    base_url: str | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    app_info: AppInfo | None = None,
    http_client: httpx.Client | None = None,
) -> GrantTokens:
    """Exchange the redirect's code for the Grant's first tokens, exactly
    once. Save the Refresh token in your token store before you use the
    Access token.

    Args:
        client_id: Your Partner app's id (`app_…`).
        client_secret: Your Partner app's secret (`tmh_as_…`).
        code: The `code` from the redirect. It works once, within 10 minutes.
        redirect_uri: The same redirect URI the consent URL carried.
        code_verifier: The verifier from the `create_pkce_pair()` behind the
            consent URL.
        environment: Which deployment the Partner app belongs to.
        base_url: Overrides the Environment's base URL, e.g. for a mock
            server.
        timeout: Seconds to wait for the response.
        app_info: Identifies your integration in the User-Agent.
        http_client: Sends the request; by default a short-lived one.

    Raises:
        OAuthError: The token endpoint refused the code.
        APIConnectionError: No response arrived. The code may have been
            consumed, so re-run consent rather than retrying.
    """
    grant = exchange_grant(
        http_client,
        make_token_endpoint(
            environment=environment,
            base_url=base_url,
            timeout=timeout,
            app_info=app_info,
            clock=None,
        ),
        _partner_app(client_id, client_secret),
        _code_exchange_form(
            code=code, redirect_uri=redirect_uri, code_verifier=code_verifier
        ),
        _CODE_EXCHANGE_GUIDANCE,
    )
    return grant.tokens


async def async_exchange_code(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    code_verifier: str,
    environment: Environment = "live",
    base_url: str | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    app_info: AppInfo | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> GrantTokens:
    """The asyncio twin of `exchange_code`."""
    grant = await async_exchange_grant(
        http_client,
        make_token_endpoint(
            environment=environment,
            base_url=base_url,
            timeout=timeout,
            app_info=app_info,
            clock=None,
        ),
        _partner_app(client_id, client_secret),
        _code_exchange_form(
            code=code, redirect_uri=redirect_uri, code_verifier=code_verifier
        ),
        _CODE_EXCHANGE_GUIDANCE,
    )
    return grant.tokens
