"""A scripted fake of the TeachMeHIPAA API, plugged in through httpx's
transport seam so tests exercise the public client end to end."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

LIVE_BASE = "https://api.tme.so/v1"
SANDBOX_BASE = "https://api-teachmehipaa-dev.web.app/v1"

CLIENT_ID = "cli_01JD8Z4N3QX5V7W9Y2B4C6D8EF"
CLIENT_SECRET = "tmh_cs_k3Jq9-Zx_8LmN2pR4tV6wY0aB1cD3eF5gH7iJ9kL0mN"
# base64("<CLIENT_ID>:<CLIENT_SECRET>"), computed outside the SDK.
BASIC_CREDENTIALS = (
    "Y2xpXzAxSkQ4WjROM1FYNVY3VzlZMkI0QzZEOEVGOnRtaF9jc19rM0pxOS1aeF84TG1OMnBS"
    "NHRWNndZMGFCMWNEM2VGNWdIN2lKOWtMMG1O"
)
ORG_ID = "org_acme"
LEARNER_ID = "sub_01JD8Z4N3QX5V7W9Y2B4C6D8EG"
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiJ9.first.sig"
SECOND_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiJ9.second.sig"
REQUEST_ID = "req_7f3c2a"
ETAG = '"9b2f0c4e1d"'

LEARNER_JSON: dict[str, Any] = {
    "learnerId": LEARNER_ID,
    "email": "ana@example.com",
    "name": "Ana Lima",
    "externalId": "hr-123",
    "status": "in_progress",
    "course": {"courseId": "hipaa-essentials", "title": "HIPAA Essentials"},
    "invitedAt": "2026-11-01T09:00:00Z",
    "startedAt": "2026-11-02T10:30:00Z",
    "completedAt": None,
    "dueAt": "2026-12-01T00:00:00Z",
    "certificate": None,
}


def token_json(access_token: str = ACCESS_TOKEN, expires_in: int = 900) -> Any:
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "scope": "learners:read learners:write",
    }


def introspection_json(org_id: str | None = ORG_ID) -> Any:
    return {
        "actorType": "client",
        "clientId": CLIENT_ID,
        "subjectId": None,
        "orgId": org_id,
        "scopes": ["learners:read", "learners:write"],
        "mode": "test",
        "expiresAt": "2026-11-15T12:15:00Z",
    }


@dataclass(frozen=True)
class Reply:
    status: int = 200
    json: Any = None
    headers: dict[str, str] = field(default_factory=dict)
    content_type: str = "application/json"
    # Sent verbatim instead of `json`, for non-JSON bodies.
    text: str | None = None
    content: bytes | None = None

    def to_response(self) -> httpx.Response:
        if self.content is not None:
            content = self.content
        else:
            content = (
                json.dumps(self.json) if self.text is None else self.text
            ).encode()
        return httpx.Response(
            self.status,
            content=content,
            headers={"content-type": self.content_type, **self.headers},
        )


def problem(
    status: int,
    code: str,
    *,
    title: str = "Problem",
    detail: str | None = None,
    errors: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> Reply:
    """An RFC 9457 problem reply shaped like the API's `problem()` helper."""
    body: dict[str, Any] = {"title": title, "status": status, "code": code}
    if detail is not None:
        body["detail"] = detail
    if errors is not None:
        body["errors"] = errors
    return Reply(
        status=status,
        json=body,
        content_type="application/problem+json",
        headers={"x-request-id": REQUEST_ID, **(headers or {})},
    )


def network_error(request: httpx.Request) -> Reply:
    raise httpx.ConnectError("connection refused", request=request)


def read_timeout(request: httpx.Request) -> Reply:
    raise httpx.ReadTimeout("timed out", request=request)


Responder = Callable[[httpx.Request], Reply]


class FakeApi:
    """Replies to scripted (method, path) routes in order; the last reply
    for a route repeats. Every request is recorded for wire assertions."""

    def __init__(self, base_url: str = LIVE_BASE) -> None:
        self.base_path = httpx.URL(base_url).path.rstrip("/")
        self.requests: list[httpx.Request] = []
        self._routes: dict[tuple[str, str], list[Reply | Responder]] = {}

    def on(self, method: str, path: str, reply: Reply | Responder) -> None:
        self._routes.setdefault((method, self.base_path + path), []).append(reply)

    def replace(self, method: str, path: str, reply: Reply | Responder) -> None:
        self._routes[(method, self.base_path + path)] = [reply]

    def requests_to(self, method: str, path: str) -> list[httpx.Request]:
        full = self.base_path + path
        return [r for r in self.requests if (r.method, r.url.path) == (method, full)]

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        queue = self._routes.get((request.method, request.url.path))
        if not queue:
            raise AssertionError(f"unscripted request {request.method} {request.url}")
        reply = queue.pop(0) if len(queue) > 1 else queue[0]
        if callable(reply):
            reply = reply(request)
        return reply.to_response()

    async def handle_async(self, request: httpx.Request) -> httpx.Response:
        # Yield to the loop the way a real network call would, so concurrent
        # callers genuinely interleave.
        await asyncio.sleep(0)
        return self.handle(request)

    def sync_client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handle))

    def async_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handle_async))


def script_learner_retrieve(api: FakeApi) -> None:
    api.on("POST", "/auth/token", Reply(json=token_json()))
    api.on("GET", "/auth/introspection", Reply(json=introspection_json()))
    api.on(
        "GET",
        f"/organizations/{ORG_ID}/learners/{LEARNER_ID}",
        Reply(json=LEARNER_JSON, headers={"x-request-id": REQUEST_ID, "etag": ETAG}),
    )


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeSleep:
    """Records each wait instead of waiting, and moves the clock on."""

    def __init__(self, clock: FakeClock | None = None) -> None:
        self.waits: list[float] = []
        self._clock = clock

    def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)
        if self._clock is not None:
            self._clock.advance(seconds)


class FakeAsyncSleep:
    def __init__(self, clock: FakeClock | None = None) -> None:
        self._sleep = FakeSleep(clock)

    @property
    def waits(self) -> list[float]:
        return self._sleep.waits

    async def __call__(self, seconds: float) -> None:
        self._sleep(seconds)
