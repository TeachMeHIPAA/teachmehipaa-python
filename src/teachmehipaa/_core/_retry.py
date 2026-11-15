"""Sending with retries (grilling Q18). The retry decisions are pure; the sync
and async senders differ only in how they send and wait."""

from __future__ import annotations

import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx

from ._errors import (
    APIConnectionError,
    AuthenticationError,
    TeachMeHipaaError,
    connection_error,
    parse_retry_after,
)

INITIAL_RETRY_DELAY = 0.5
MAX_RETRY_DELAY = 5.0
MAX_RETRY_AFTER = 60.0

ErrorMapper = Callable[[httpx.Response], TeachMeHipaaError]
# Told which request was refused so the token it carried can be dropped;
# answers whether a replay could succeed, which it can't with the same token.
Replay = Callable[[httpx.Request], bool]
AsyncReplay = Callable[[httpx.Request], Awaitable[bool]]


@dataclass(frozen=True)
class RetryPolicy:
    """Whether and how often one call may be retried. Only retry-safe calls
    retry: replaying anything else after a lost response could apply it
    twice."""

    retry_safe: bool
    max_retries: int


def is_transient(error: TeachMeHipaaError) -> bool:
    if isinstance(error, APIConnectionError):
        return True
    status = error.status
    if status is None:
        return False
    # Other 409 codes are business conflicts that a replay can't fix;
    # `conflict` means the same Idempotency-Key is still in flight.
    return (
        status >= 500 or status == 429 or (status == 409 and error.code == "conflict")
    )


def retry_delay(retry: int, error: TeachMeHipaaError) -> float:
    retry_after = parse_retry_after(error.headers)
    if retry_after is not None:
        return min(retry_after, MAX_RETRY_AFTER)
    nominal = min(INITIAL_RETRY_DELAY * 2.0**retry, MAX_RETRY_DELAY)
    # Jitter spreads clients that failed together; it is not security.
    jittered = nominal * (0.5 + random.random() / 2)  # noqa: S311
    return max(INITIAL_RETRY_DELAY, jittered)


def is_unauthorized(error: TeachMeHipaaError) -> bool:
    return isinstance(error, AuthenticationError) and error.code == "unauthorized"


def _next_delay(
    policy: RetryPolicy, retries: int, error: TeachMeHipaaError
) -> float | None:
    if policy.retry_safe and retries < policy.max_retries and is_transient(error):
        return retry_delay(retries, error)
    return None


class SyncSender:
    def __init__(
        self, http_client: httpx.Client, sleep: Callable[[float], None]
    ) -> None:
        self._http_client = http_client
        self.sleep = sleep

    def send(
        self,
        make_request: Callable[[], httpx.Request],
        map_error: ErrorMapper,
        policy: RetryPolicy,
        replay: Replay | None = None,
        *,
        stream: bool = False,
    ) -> httpx.Response:
        """With `stream`, a success comes back with its body unread; an error
        is still read, to map it, and closed."""
        retries = 0
        replayed = False
        while True:
            request = make_request()
            try:
                response = self._http_client.send(request, stream=stream)
                if response.is_error and stream:
                    try:
                        response.read()
                    finally:
                        response.close()
            except httpx.TransportError as exc:
                error: TeachMeHipaaError = connection_error(exc)
            else:
                if not response.is_error:
                    return response
                error = map_error(response)
            # A token revoked mid-flight earns one fresh token and a replay,
            # outside the retry budget: it says nothing about the API's health.
            if replay is not None and not replayed and is_unauthorized(error):
                replayed = True
                if replay(request):
                    continue
            delay = _next_delay(policy, retries, error)
            if delay is None:
                raise error
            self.sleep(delay)
            retries += 1


class AsyncSender:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        sleep: Callable[[float], Awaitable[None]],
    ) -> None:
        self._http_client = http_client
        self.sleep = sleep

    async def send(
        self,
        make_request: Callable[[], Awaitable[httpx.Request]],
        map_error: ErrorMapper,
        policy: RetryPolicy,
        replay: AsyncReplay | None = None,
        *,
        stream: bool = False,
    ) -> httpx.Response:
        """With `stream`, a success comes back with its body unread; an error
        is still read, to map it, and closed."""
        retries = 0
        replayed = False
        while True:
            request = await make_request()
            try:
                response = await self._http_client.send(request, stream=stream)
                if response.is_error and stream:
                    try:
                        await response.aread()
                    finally:
                        await response.aclose()
            except httpx.TransportError as exc:
                error: TeachMeHipaaError = connection_error(exc)
            else:
                if not response.is_error:
                    return response
                error = map_error(response)
            # A token revoked mid-flight earns one fresh token and a replay,
            # outside the retry budget: it says nothing about the API's health.
            if replay is not None and not replayed and is_unauthorized(error):
                replayed = True
                if await replay(request):
                    continue
            delay = _next_delay(policy, retries, error)
            if delay is None:
                raise error
            await self.sleep(delay)
            retries += 1
