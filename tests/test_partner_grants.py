import asyncio
import threading
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest

from teachmehipaa import (
    APIConnectionError,
    AsyncPartnerGrantTokenProvider,
    AsyncTeachMeHipaa,
    OAuthError,
    PartnerGrantTokenProvider,
    TeachMeHipaa,
    TokenStoreError,
)
from tests.fake_api import (
    APP_BASIC_CREDENTIALS,
    APP_ID,
    APP_SECRET,
    LEARNER_ID,
    LEARNER_JSON,
    ORG_ID,
    REFRESH_TOKEN_1,
    REFRESH_TOKEN_2,
    REFRESH_TOKEN_3,
    FakeApi,
    FakeClock,
    Reply,
    grant_token_reply,
    network_error,
    oauth_error_reply,
    problem,
)

LEARNER_PATH = f"/organizations/{ORG_ID}/learners/{LEARNER_ID}"
TOKEN_PATH = "/auth/token"


class MemoryStore:
    """A token store that records, at each save, which requests the API had
    already seen, so ordering is asserted on the wire."""

    def __init__(self, api: FakeApi, initial: str = REFRESH_TOKEN_1) -> None:
        self.saved: list[str] = []
        self.requests_seen_at_save: list[list[str]] = []
        self._api = api
        self._initial = initial

    def load(self) -> str:
        return self.saved[-1] if self.saved else self._initial

    def save(self, refresh_token: str) -> None:
        self.requests_seen_at_save.append([r.url.path for r in self._api.requests])
        self.saved.append(refresh_token)


def form_of(request_content: bytes) -> dict[str, list[str]]:
    return parse_qs(request_content.decode())


def test_the_rotated_refresh_token_is_saved_before_the_api_request_is_sent() -> None:
    api = FakeApi()
    api.on("POST", TOKEN_PATH, grant_token_reply("jwt-org", REFRESH_TOKEN_2))
    api.on("GET", LEARNER_PATH, Reply(json=LEARNER_JSON))
    store = MemoryStore(api)
    client = TeachMeHipaa(
        token_provider=PartnerGrantTokenProvider(
            client_id=APP_ID,
            client_secret=APP_SECRET,
            token_store=store,
            http_client=api.sync_client(),
        ),
        organization_id=ORG_ID,
        http_client=api.sync_client(),
    )

    client.learners.retrieve(LEARNER_ID)

    assert store.saved == [REFRESH_TOKEN_2]
    assert store.requests_seen_at_save == [["/v1/auth/token"]]
    [exchange] = api.requests_to("POST", TOKEN_PATH)
    assert exchange.headers["authorization"] == f"Basic {APP_BASIC_CREDENTIALS}"
    assert form_of(exchange.content) == {
        "grant_type": ["refresh_token"],
        "refresh_token": [REFRESH_TOKEN_1],
    }
    [learner_request] = api.requests_to("GET", LEARNER_PATH)
    assert learner_request.headers["authorization"] == "Bearer jwt-org"


class AsyncMemoryStore:
    def __init__(self, api: FakeApi, initial: str = REFRESH_TOKEN_1) -> None:
        self._store = MemoryStore(api, initial)

    @property
    def saved(self) -> list[str]:
        return self._store.saved

    @property
    def requests_seen_at_save(self) -> list[list[str]]:
        return self._store.requests_seen_at_save

    async def load(self) -> str:
        return self._store.load()

    async def save(self, refresh_token: str) -> None:
        # Yield like a real database write, so a save that isn't awaited
        # would land after the API request.
        await asyncio.sleep(0)
        self._store.save(refresh_token)


class ReadOnlyStore:
    """Saves fail for the first `failures` calls."""

    def __init__(self, failures: int = 1) -> None:
        self.attempted: list[str] = []
        self._failures = failures

    def load(self) -> str:
        return REFRESH_TOKEN_1

    def save(self, refresh_token: str) -> None:
        self.attempted.append(refresh_token)
        if len(self.attempted) <= self._failures:
            raise OSError("database is read-only")


def grant_client(
    api: FakeApi,
    store: Any,
    *,
    clock: FakeClock | None = None,
    **provider_options: Any,
) -> TeachMeHipaa:
    return TeachMeHipaa(
        token_provider=PartnerGrantTokenProvider(
            client_id=APP_ID,
            client_secret=APP_SECRET,
            token_store=store,
            http_client=api.sync_client(),
            clock=clock,
            **provider_options,
        ),
        organization_id=ORG_ID,
        http_client=api.sync_client(),
        clock=clock,
    )


def async_grant_client(api: FakeApi, store: Any) -> AsyncTeachMeHipaa:
    return AsyncTeachMeHipaa(
        token_provider=AsyncPartnerGrantTokenProvider(
            client_id=APP_ID,
            client_secret=APP_SECRET,
            token_store=store,
            http_client=api.async_client(),
        ),
        organization_id=ORG_ID,
        http_client=api.async_client(),
    )


def refresh_tokens_sent(api: FakeApi) -> list[str]:
    return [
        form_of(r.content)["refresh_token"][0]
        for r in api.requests_to("POST", TOKEN_PATH)
    ]


def bearers(api: FakeApi) -> list[str]:
    return [r.headers["authorization"] for r in api.requests_to("GET", LEARNER_PATH)]


async def test_the_async_provider_saves_before_the_api_request_is_sent() -> None:
    api = FakeApi()
    api.on("POST", TOKEN_PATH, grant_token_reply("jwt-org", REFRESH_TOKEN_2))
    api.on("GET", LEARNER_PATH, Reply(json=LEARNER_JSON))
    store = AsyncMemoryStore(api)

    await async_grant_client(api, store).learners.retrieve(LEARNER_ID)

    assert store.saved == [REFRESH_TOKEN_2]
    assert store.requests_seen_at_save == [["/v1/auth/token"]]
    assert bearers(api) == ["Bearer jwt-org"]


def test_a_failed_save_aborts_the_call_without_using_the_access_token() -> None:
    api = FakeApi()
    api.on("POST", TOKEN_PATH, grant_token_reply("jwt-org", REFRESH_TOKEN_2))

    with pytest.raises(
        TokenStoreError, match=r"token_store\.save\(\) failed"
    ) as raised:
        grant_client(api, ReadOnlyStore()).learners.retrieve(LEARNER_ID)

    assert isinstance(raised.value.__cause__, OSError)
    assert REFRESH_TOKEN_2 not in str(raised.value)
    assert "jwt-org" not in str(raised.value)
    assert api.requests_to("GET", LEARNER_PATH) == []


async def test_a_failed_async_save_aborts_the_call() -> None:
    class FailingStore:
        async def load(self) -> str:
            return REFRESH_TOKEN_1

        async def save(self, refresh_token: str) -> None:
            raise OSError("database is read-only")

    api = FakeApi()
    api.on("POST", TOKEN_PATH, grant_token_reply("jwt-org", REFRESH_TOKEN_2))

    with pytest.raises(TokenStoreError) as raised:
        await async_grant_client(api, FailingStore()).learners.retrieve(LEARNER_ID)

    assert isinstance(raised.value.__cause__, OSError)
    assert api.requests_to("GET", LEARNER_PATH) == []


def test_after_a_failed_save_the_rotated_refresh_token_is_presented() -> None:
    api = FakeApi()
    api.on("POST", TOKEN_PATH, grant_token_reply("jwt-1", REFRESH_TOKEN_2))
    api.on("POST", TOKEN_PATH, grant_token_reply("jwt-2", REFRESH_TOKEN_3))
    api.on("GET", LEARNER_PATH, Reply(json=LEARNER_JSON))
    store = ReadOnlyStore(failures=1)
    client = grant_client(api, store)

    with pytest.raises(TokenStoreError):
        client.learners.retrieve(LEARNER_ID)
    client.learners.retrieve(LEARNER_ID)

    assert refresh_tokens_sent(api) == [REFRESH_TOKEN_1, REFRESH_TOKEN_2]
    assert store.attempted == [REFRESH_TOKEN_2, REFRESH_TOKEN_3]


def test_a_network_error_during_refresh_makes_exactly_one_exchange_attempt() -> None:
    api = FakeApi()
    api.on("POST", TOKEN_PATH, network_error)
    store = MemoryStore(api)

    with pytest.raises(APIConnectionError) as raised:
        grant_client(api, store).learners.retrieve(LEARNER_ID)

    assert "not retried" in str(raised.value)
    assert "re-run consent" in str(raised.value)
    assert isinstance(raised.value.__cause__, httpx.ConnectError)
    assert len(api.requests_to("POST", TOKEN_PATH)) == 1
    assert store.saved == []


async def test_an_async_network_error_during_refresh_makes_one_attempt() -> None:
    api = FakeApi()
    api.on("POST", TOKEN_PATH, network_error)
    store = AsyncMemoryStore(api)

    with pytest.raises(APIConnectionError, match="not retried"):
        await async_grant_client(api, store).learners.retrieve(LEARNER_ID)

    assert len(api.requests_to("POST", TOKEN_PATH)) == 1
    assert store.saved == []


def test_a_server_error_during_refresh_is_not_retried() -> None:
    api = FakeApi()
    api.on(
        "POST",
        TOKEN_PATH,
        oauth_error_reply("temporarily_unavailable", "Try later", status=503),
    )

    with pytest.raises(OAuthError):
        grant_client(api, MemoryStore(api)).learners.retrieve(LEARNER_ID)

    assert len(api.requests_to("POST", TOKEN_PATH)) == 1


def test_invalid_grant_says_the_grant_was_revoked_or_its_token_reused() -> None:
    api = FakeApi()
    api.on(
        "POST",
        TOKEN_PATH,
        oauth_error_reply("invalid_grant", "Refresh token is invalid"),
    )

    with pytest.raises(OAuthError) as raised:
        grant_client(api, MemoryStore(api)).learners.retrieve(LEARNER_ID)

    assert raised.value.code == "invalid_grant"
    assert raised.value.status == 400
    message = str(raised.value)
    assert "revoked" in message
    assert "reused" in message
    assert "Re-run consent" in message
    assert len(api.requests_to("POST", TOKEN_PATH)) == 1


def test_concurrent_calls_exchange_the_refresh_token_once() -> None:
    api = FakeApi()
    exchange_started = threading.Event()
    second_exchange = threading.Event()
    exchanges = 0

    def slow_token_endpoint(request: httpx.Request) -> Reply:
        nonlocal exchanges
        exchanges += 1
        exchange_started.set()
        if exchanges > 1:
            second_exchange.set()
        # Hold the first exchange open until the other caller is waiting on
        # it, or until a duplicate exchange proves it isn't.
        second_exchange.wait(timeout=0.2)
        return grant_token_reply("jwt-org", REFRESH_TOKEN_2)

    api.on("POST", TOKEN_PATH, slow_token_endpoint)
    api.on("GET", LEARNER_PATH, Reply(json=LEARNER_JSON))
    store = MemoryStore(api)
    client = grant_client(api, store)
    first = threading.Thread(target=client.learners.retrieve, args=(LEARNER_ID,))
    second = threading.Thread(target=client.learners.retrieve, args=(LEARNER_ID,))

    first.start()
    exchange_started.wait(timeout=1)
    second.start()
    first.join()
    second.join()

    assert exchanges == 1
    assert store.saved == [REFRESH_TOKEN_2]
    assert len(api.requests_to("GET", LEARNER_PATH)) == 2


async def test_concurrent_async_calls_exchange_the_refresh_token_once() -> None:
    api = FakeApi()
    api.on("POST", TOKEN_PATH, grant_token_reply("jwt-org", REFRESH_TOKEN_2))
    api.on("GET", LEARNER_PATH, Reply(json=LEARNER_JSON))
    store = AsyncMemoryStore(api)
    client = async_grant_client(api, store)

    await asyncio.gather(*(client.learners.retrieve(LEARNER_ID) for _ in range(5)))

    assert len(api.requests_to("POST", TOKEN_PATH)) == 1
    assert store.saved == [REFRESH_TOKEN_2]
    assert bearers(api) == ["Bearer jwt-org"] * 5


def test_re_mints_60_seconds_before_expiry_with_the_rotated_refresh_token(
    clock: FakeClock,
) -> None:
    api = FakeApi()
    api.on("POST", TOKEN_PATH, grant_token_reply("jwt-1", REFRESH_TOKEN_2, 900))
    api.on("POST", TOKEN_PATH, grant_token_reply("jwt-2", REFRESH_TOKEN_3, 900))
    api.on("GET", LEARNER_PATH, Reply(json=LEARNER_JSON))
    store = MemoryStore(api)
    client = grant_client(api, store, clock=clock)

    client.learners.retrieve(LEARNER_ID)
    clock.advance(839)  # expires_in 900, so still 61 s of life left
    client.learners.retrieve(LEARNER_ID)
    clock.advance(1)  # 60 s left: renew now
    client.learners.retrieve(LEARNER_ID)

    assert refresh_tokens_sent(api) == [REFRESH_TOKEN_1, REFRESH_TOKEN_2]
    assert store.saved == [REFRESH_TOKEN_2, REFRESH_TOKEN_3]
    assert bearers(api) == ["Bearer jwt-1", "Bearer jwt-1", "Bearer jwt-2"]


def test_a_401_re_mints_once_and_replays_the_request() -> None:
    api = FakeApi()
    api.on("POST", TOKEN_PATH, grant_token_reply("jwt-1", REFRESH_TOKEN_2))
    api.on("POST", TOKEN_PATH, grant_token_reply("jwt-2", REFRESH_TOKEN_3))
    api.on("GET", LEARNER_PATH, problem(401, "unauthorized"))
    api.on("GET", LEARNER_PATH, Reply(json=LEARNER_JSON))

    grant_client(api, MemoryStore(api)).learners.retrieve(LEARNER_ID)

    assert refresh_tokens_sent(api) == [REFRESH_TOKEN_1, REFRESH_TOKEN_2]
    assert bearers(api) == ["Bearer jwt-1", "Bearer jwt-2"]


def test_a_refresh_token_passed_up_front_is_used_for_the_first_exchange() -> None:
    api = FakeApi()
    api.on("POST", TOKEN_PATH, grant_token_reply("jwt-org", REFRESH_TOKEN_3))
    api.on("GET", LEARNER_PATH, Reply(json=LEARNER_JSON))
    store = MemoryStore(api, initial="tmh_rt_never_loaded")

    grant_client(api, store, refresh_token=REFRESH_TOKEN_2).learners.retrieve(
        LEARNER_ID
    )

    assert refresh_tokens_sent(api) == [REFRESH_TOKEN_2]
    assert store.saved == [REFRESH_TOKEN_3]


def test_scopes_narrow_the_access_token() -> None:
    api = FakeApi()
    api.on("POST", TOKEN_PATH, grant_token_reply("jwt-org", REFRESH_TOKEN_2))
    api.on("GET", LEARNER_PATH, Reply(json=LEARNER_JSON))

    grant_client(api, MemoryStore(api), scopes=["learners:read"]).learners.retrieve(
        LEARNER_ID
    )

    [exchange] = api.requests_to("POST", TOKEN_PATH)
    assert form_of(exchange.content)["scope"] == ["learners:read"]


def test_a_store_that_loads_no_refresh_token_raises_before_any_exchange() -> None:
    api = FakeApi()

    with pytest.raises(TokenStoreError, match="no Refresh token"):
        grant_client(api, MemoryStore(api, initial="")).learners.retrieve(LEARNER_ID)

    assert api.requests == []
