import asyncio
import threading
from urllib.parse import parse_qs

import httpx
import pytest

from teachmehipaa import AsyncTeachMeHipaa, TeachMeHipaa, TeachMeHipaaError
from tests.fake_api import (
    ACCESS_TOKEN,
    BASIC_CREDENTIALS,
    CLIENT_ID,
    CLIENT_SECRET,
    LEARNER_ID,
    LEARNER_JSON,
    ORG_ID,
    SECOND_ACCESS_TOKEN,
    FakeApi,
    FakeClock,
    Reply,
    token_json,
)

LEARNER_PATH = f"/organizations/{ORG_ID}/learners/{LEARNER_ID}"


def bearer_tokens_sent(api: FakeApi) -> list[str]:
    return [r.headers["authorization"] for r in api.requests_to("GET", LEARNER_PATH)]


def test_mints_a_token_with_http_basic_client_credentials(api: FakeApi) -> None:
    client = TeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, http_client=api.sync_client()
    )

    client.learners.retrieve(LEARNER_ID)

    [mint] = api.requests_to("POST", "/auth/token")
    assert mint.headers["authorization"] == f"Basic {BASIC_CREDENTIALS}"
    assert mint.headers["content-type"] == "application/x-www-form-urlencoded"
    assert parse_qs(mint.content.decode()) == {"grant_type": ["client_credentials"]}


def test_requests_only_the_scopes_given(api: FakeApi) -> None:
    client = TeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=["learners:read", "compliance:read"],
        http_client=api.sync_client(),
    )

    client.learners.retrieve(LEARNER_ID)

    [mint] = api.requests_to("POST", "/auth/token")
    assert parse_qs(mint.content.decode()) == {
        "grant_type": ["client_credentials"],
        "scope": ["learners:read compliance:read"],
    }


def test_reuses_a_cached_token_across_calls(api: FakeApi) -> None:
    client = TeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, http_client=api.sync_client()
    )

    client.learners.retrieve(LEARNER_ID)
    client.learners.retrieve(LEARNER_ID)

    assert len(api.requests_to("POST", "/auth/token")) == 1
    assert bearer_tokens_sent(api) == [f"Bearer {ACCESS_TOKEN}"] * 2


def test_re_mints_a_token_60_seconds_before_it_expires(
    api: FakeApi, clock: FakeClock
) -> None:
    api.on("POST", "/auth/token", Reply(json=token_json(SECOND_ACCESS_TOKEN)))
    client = TeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.sync_client(),
        clock=clock,
    )

    client.learners.retrieve(LEARNER_ID)
    clock.advance(839)  # expires_in 900, so still 61 s of life left
    client.learners.retrieve(LEARNER_ID)
    clock.advance(1)  # 60 s left: renew now
    client.learners.retrieve(LEARNER_ID)

    assert len(api.requests_to("POST", "/auth/token")) == 2
    assert bearer_tokens_sent(api) == [
        f"Bearer {ACCESS_TOKEN}",
        f"Bearer {ACCESS_TOKEN}",
        f"Bearer {SECOND_ACCESS_TOKEN}",
    ]


def test_concurrent_calls_mint_exactly_one_token() -> None:
    api = FakeApi()
    mint_started = threading.Event()
    second_mint = threading.Event()
    mints = 0

    def slow_token_endpoint(request: httpx.Request) -> Reply:
        nonlocal mints
        mints += 1
        mint_started.set()
        if mints > 1:
            second_mint.set()
        # Hold the first mint open long enough for the other caller to be
        # waiting on it, or until a duplicate mint proves it isn't.
        second_mint.wait(timeout=0.2)
        return Reply(json=token_json())

    api.on("POST", "/auth/token", slow_token_endpoint)
    api.on("GET", LEARNER_PATH, Reply(json=LEARNER_JSON))
    client = TeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.sync_client(),
    )
    first = threading.Thread(target=client.learners.retrieve, args=(LEARNER_ID,))
    second = threading.Thread(target=client.learners.retrieve, args=(LEARNER_ID,))

    first.start()
    mint_started.wait(timeout=1)
    second.start()
    first.join()
    second.join()

    assert mints == 1
    assert len(api.requests_to("GET", LEARNER_PATH)) == 2


async def test_concurrent_async_calls_mint_exactly_one_token(api: FakeApi) -> None:
    client = AsyncTeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.async_client(),
    )

    await asyncio.gather(*(client.learners.retrieve(LEARNER_ID) for _ in range(5)))

    assert len(api.requests_to("POST", "/auth/token")) == 1
    assert bearer_tokens_sent(api) == [f"Bearer {ACCESS_TOKEN}"] * 5


def test_a_rejected_credential_raises_with_the_oauth_error() -> None:
    api = FakeApi()
    api.on(
        "POST",
        "/auth/token",
        Reply(
            status=401,
            json={"error": "invalid_client", "error_description": "Unknown client."},
            headers={"x-request-id": "req_auth"},
        ),
    )
    client = TeachMeHipaa(
        client_id=CLIENT_ID, client_secret="tmh_cs_wrong", http_client=api.sync_client()
    )

    with pytest.raises(TeachMeHipaaError) as raised:
        client.learners.retrieve(LEARNER_ID)

    assert raised.value.status == 401
    assert raised.value.code == "invalid_client"
    assert raised.value.detail == "Unknown client."
    assert raised.value.request_id == "req_auth"
    assert api.requests_to("GET", LEARNER_PATH) == []
