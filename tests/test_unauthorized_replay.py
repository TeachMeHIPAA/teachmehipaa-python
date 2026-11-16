import asyncio

import httpx
import pytest

from teachmehipaa import AsyncTeachMeHipaa, AuthenticationError, TeachMeHipaa
from tests.fake_api import (
    ACCESS_TOKEN,
    CLIENT_ID,
    CLIENT_SECRET,
    LEARNER_ID,
    LEARNER_JSON,
    ORG_ID,
    SECOND_ACCESS_TOKEN,
    FakeApi,
    FakeAsyncSleep,
    FakeSleep,
    Reply,
    problem,
    token_json,
)

LEARNER_PATH = f"/organizations/{ORG_ID}/learners/{LEARNER_ID}"
REMIND_PATH = f"{LEARNER_PATH}:remind"
OK = Reply(json=LEARNER_JSON)
UNAUTHORIZED = problem(
    401,
    "unauthorized",
    title="Unauthorized",
    headers={"www-authenticate": 'Bearer error="invalid_token"'},
)


@pytest.fixture
def api() -> FakeApi:
    fake = FakeApi()
    fake.on("POST", "/auth/token", Reply(json=token_json(ACCESS_TOKEN)))
    fake.on("POST", "/auth/token", Reply(json=token_json(SECOND_ACCESS_TOKEN)))
    return fake


def make_client(api: FakeApi, *, max_retries: int = 2) -> TeachMeHipaa:
    return TeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        max_retries=max_retries,
        http_client=api.sync_client(),
        sleep=FakeSleep(),
    )


def bearers(api: FakeApi, method: str, path: str) -> list[str]:
    return [r.headers["authorization"] for r in api.requests_to(method, path)]


def mints(api: FakeApi) -> int:
    return len(api.requests_to("POST", "/auth/token"))


def test_a_revoked_token_is_re_minted_once_and_the_request_replayed(
    api: FakeApi,
) -> None:
    api.on("GET", LEARNER_PATH, UNAUTHORIZED)
    api.on("GET", LEARNER_PATH, OK)

    learner = make_client(api).learners.retrieve(LEARNER_ID)

    assert learner.learner_id == LEARNER_ID
    assert mints(api) == 2
    assert bearers(api, "GET", LEARNER_PATH) == [
        f"Bearer {ACCESS_TOKEN}",
        f"Bearer {SECOND_ACCESS_TOKEN}",
    ]


def test_the_replay_does_not_count_as_a_retry(api: FakeApi) -> None:
    api.on("GET", LEARNER_PATH, UNAUTHORIZED)
    api.on("GET", LEARNER_PATH, OK)

    learner = make_client(api, max_retries=0).learners.retrieve(LEARNER_ID)

    assert learner.learner_id == LEARNER_ID


def test_retries_are_still_available_after_a_replay(api: FakeApi) -> None:
    api.on("GET", LEARNER_PATH, UNAUTHORIZED)
    api.on("GET", LEARNER_PATH, problem(503, "temporarily_unavailable"))
    api.on("GET", LEARNER_PATH, problem(503, "temporarily_unavailable"))
    api.on("GET", LEARNER_PATH, OK)

    make_client(api).learners.retrieve(LEARNER_ID)

    assert len(api.requests_to("GET", LEARNER_PATH)) == 4


def test_a_second_401_raises_the_authentication_error(api: FakeApi) -> None:
    api.on("GET", LEARNER_PATH, UNAUTHORIZED)

    with pytest.raises(AuthenticationError) as raised:
        make_client(api).learners.retrieve(LEARNER_ID)

    assert raised.value.code == "unauthorized"
    assert len(api.requests_to("GET", LEARNER_PATH)) == 2
    assert mints(api) == 2


def test_a_replay_is_not_spent_twice_in_one_call(api: FakeApi) -> None:
    api.on("GET", LEARNER_PATH, UNAUTHORIZED)
    api.on("GET", LEARNER_PATH, problem(503, "temporarily_unavailable"))
    api.on("GET", LEARNER_PATH, UNAUTHORIZED)
    api.on("GET", LEARNER_PATH, OK)

    with pytest.raises(AuthenticationError):
        make_client(api).learners.retrieve(LEARNER_ID)

    assert len(api.requests_to("GET", LEARNER_PATH)) == 3


def test_a_replayed_write_keeps_its_idempotency_key(api: FakeApi) -> None:
    api.on("POST", REMIND_PATH, UNAUTHORIZED)
    api.on(
        "POST",
        REMIND_PATH,
        Reply(status=202, json={"learnerId": LEARNER_ID, "action": "remind"}),
    )

    make_client(api, max_retries=0).learners.remind(LEARNER_ID)

    first, replayed = api.requests_to("POST", REMIND_PATH)
    assert first.headers["idempotency-key"] == replayed.headers["idempotency-key"]
    assert replayed.headers["authorization"] == f"Bearer {SECOND_ACCESS_TOKEN}"


async def test_the_async_client_re_mints_and_replays(api: FakeApi) -> None:
    api.on("GET", LEARNER_PATH, UNAUTHORIZED)
    api.on("GET", LEARNER_PATH, OK)
    client = AsyncTeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        max_retries=0,
        http_client=api.async_client(),
        sleep=FakeAsyncSleep(),
    )

    learner = await client.learners.retrieve(LEARNER_ID)

    assert learner.learner_id == LEARNER_ID
    assert bearers(api, "GET", LEARNER_PATH)[-1] == f"Bearer {SECOND_ACCESS_TOKEN}"


async def test_concurrent_401s_re_mint_one_token(api: FakeApi) -> None:
    def revoked_first_token(request: httpx.Request) -> Reply:
        if request.headers["authorization"] == f"Bearer {ACCESS_TOKEN}":
            return UNAUTHORIZED
        return OK

    api.on("GET", LEARNER_PATH, revoked_first_token)
    client = AsyncTeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.async_client(),
        sleep=FakeAsyncSleep(),
    )

    await asyncio.gather(*(client.learners.retrieve(LEARNER_ID) for _ in range(3)))

    assert mints(api) == 2
