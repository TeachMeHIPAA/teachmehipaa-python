"""One `authorization_code` or `refresh_token` exchange, sent exactly once.

Replaying a spent code or a superseded Refresh token revokes the Grant
(ADR-0004), so a failure is raised with guidance instead of retried.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from dataclasses import dataclass, field

import httpx

from ._auth import ClientCredentials
from ._config import TokenEndpoint
from ._errors import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    OAuthError,
    TeachMeHipaaError,
    is_json,
    oauth_error_from_response,
    unexpected_response_error,
)
from ._retry import AsyncSender, RetryPolicy, SyncSender

# Replaying a spent code or a superseded Refresh token revokes the Grant
# (ADR-0004), so an exchange is sent once: with no retries allowed, the
# sender never reaches its sleep.
_NEVER_RETRY = RetryPolicy(retry_safe=False, max_retries=0)


@dataclass(frozen=True)
class GrantTokens:
    """What a Grant's token exchange returns."""

    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    """Replaces the one exchanged; save it before anything else."""
    expires_in: float
    """Seconds until the Access token expires."""
    scopes: tuple[str, ...]
    """The Scopes the Access token carries."""


@dataclass(frozen=True)
class GrantExchange:
    tokens: GrantTokens
    requested_at: float
    """When the request left, so expiry can't stretch past the real
    lifetime."""

    @property
    def expires_at(self) -> float:
        return self.requested_at + self.tokens.expires_in


@dataclass(frozen=True)
class ExchangeGuidance:
    """What to tell the caller when an exchange fails in a way only they can
    fix."""

    network_failure: str
    """For a network failure, whose outcome is unknown."""
    invalid_grant: str | None = None
    """For `invalid_grant`, or None to keep the endpoint's words."""


def _append(message: str, guidance: str) -> str:
    return f"{message.rstrip('.')}. {guidance}"


def _with_guidance(
    error: TeachMeHipaaError, guidance: ExchangeGuidance
) -> TeachMeHipaaError:
    guided: TeachMeHipaaError
    if isinstance(error, APIConnectionError):
        message = _append(error.message, guidance.network_failure)
        if isinstance(error, APITimeoutError):
            guided = APITimeoutError(message)
        else:
            guided = APIConnectionError(message)
    elif (
        isinstance(error, OAuthError)
        and error.code == "invalid_grant"
        and guidance.invalid_grant is not None
    ):
        guided = OAuthError(
            _append(error.message, guidance.invalid_grant),
            status=error.status,
            code=error.code,
            detail=error.detail,
            request_id=error.request_id,
            headers=error.headers,
            body=error.body,
        )
    else:
        return error
    return guided


def _not_a_grant() -> APIError:
    # No body or headers: the body may hold a live Access token, which must
    # not reach error reporters.
    return APIError(
        "The token endpoint answered without an access_token, refresh_token "
        "and expires_in.",
        status=200,
    )


def _read_grant(response: httpx.Response, *, requested_at: float) -> GrantExchange:
    if not is_json(response):
        raise unexpected_response_error(response)
    body = response.json()
    if not isinstance(body, dict):
        raise _not_a_grant()
    access_token = body.get("access_token")
    refresh_token = body.get("refresh_token")
    expires_in = body.get("expires_in")
    if (
        not isinstance(access_token, str)
        or not isinstance(refresh_token, str)
        or not refresh_token
        or not isinstance(expires_in, (int, float))
    ):
        raise _not_a_grant()
    scope = body.get("scope")
    return GrantExchange(
        tokens=GrantTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=float(expires_in),
            scopes=tuple(scope.split()) if isinstance(scope, str) else (),
        ),
        requested_at=requested_at,
    )


def exchange_grant(
    http_client: httpx.Client | None,
    endpoint: TokenEndpoint,
    credentials: ClientCredentials,
    form: Mapping[str, str],
    guidance: ExchangeGuidance,
) -> GrantExchange:
    """Without an `http_client`, a short-lived one carries the exchange, so
    nothing needs closing between exchanges minutes apart."""
    requested_at = endpoint.clock()
    try:
        if http_client is None:
            with httpx.Client(timeout=endpoint.timeout) as owned:
                response = _send(owned, endpoint, credentials, form)
        else:
            response = _send(http_client, endpoint, credentials, form)
    except TeachMeHipaaError as error:
        raise _with_guidance(error, guidance) from error.__cause__
    return _read_grant(response, requested_at=requested_at)


def _send(
    http_client: httpx.Client,
    endpoint: TokenEndpoint,
    credentials: ClientCredentials,
    form: Mapping[str, str],
) -> httpx.Response:
    return SyncSender(http_client, time.sleep).send(
        lambda: credentials.token_request(
            endpoint.url, form, user_agent=endpoint.user_agent, timeout=endpoint.timeout
        ),
        oauth_error_from_response,
        _NEVER_RETRY,
    )


async def async_exchange_grant(
    http_client: httpx.AsyncClient | None,
    endpoint: TokenEndpoint,
    credentials: ClientCredentials,
    form: Mapping[str, str],
    guidance: ExchangeGuidance,
) -> GrantExchange:
    """The asyncio twin of `exchange_grant`."""
    requested_at = endpoint.clock()
    try:
        if http_client is None:
            async with httpx.AsyncClient(timeout=endpoint.timeout) as owned:
                response = await _async_send(owned, endpoint, credentials, form)
        else:
            response = await _async_send(http_client, endpoint, credentials, form)
    except TeachMeHipaaError as error:
        raise _with_guidance(error, guidance) from error.__cause__
    return _read_grant(response, requested_at=requested_at)


async def _async_send(
    http_client: httpx.AsyncClient,
    endpoint: TokenEndpoint,
    credentials: ClientCredentials,
    form: Mapping[str, str],
) -> httpx.Response:
    async def make_request() -> httpx.Request:
        return credentials.token_request(
            endpoint.url, form, user_agent=endpoint.user_agent, timeout=endpoint.timeout
        )

    return await AsyncSender(http_client, asyncio.sleep).send(
        make_request, oauth_error_from_response, _NEVER_RETRY
    )
