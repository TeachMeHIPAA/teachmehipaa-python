import json
import uuid

import pytest

from teachmehipaa import (
    APIConnectionError,
    APIError,
    AsyncTeachMeHipaa,
    IdempotencyError,
    TeachMeHipaa,
)
from tests.fake_api import (
    CLIENT_ID,
    CLIENT_SECRET,
    ETAG,
    LEARNER_ID,
    LEARNER_JSON,
    ORG_ID,
    FakeApi,
    FakeAsyncSleep,
    FakeSleep,
    Reply,
    network_error,
    problem,
    token_json,
)

LEARNER_PATH = f"/organizations/{ORG_ID}/learners/{LEARNER_ID}"
REMIND_PATH = f"{LEARNER_PATH}:remind"
LAUNCH_LINK_PATH = f"{LEARNER_PATH}:createLaunchLink"
REMIND_ACCEPTED = Reply(status=202, json={"learnerId": LEARNER_ID, "action": "remind"})
LAUNCH_LINK = Reply(
    json={
        "url": "https://training.teachmehipaa.com/launch/abc123",
        "expiresAt": "2026-11-15T12:05:00Z",
    }
)
UNAVAILABLE = problem(503, "temporarily_unavailable")


@pytest.fixture
def api() -> FakeApi:
    fake = FakeApi()
    fake.on("POST", "/auth/token", Reply(json=token_json()))
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


def keys_sent(api: FakeApi, path: str) -> list[str | None]:
    return [r.headers.get("idempotency-key") for r in api.requests_to("POST", path)]


def test_a_call_that_requires_a_key_sends_a_generated_uuid4(api: FakeApi) -> None:
    api.on("POST", REMIND_PATH, REMIND_ACCEPTED)

    accepted = make_client(api).learners.remind(LEARNER_ID)

    assert (accepted.learner_id, accepted.action) == (LEARNER_ID, "remind")
    [key] = keys_sent(api, REMIND_PATH)
    assert key is not None
    assert uuid.UUID(key).version == 4


def test_each_call_gets_a_new_key(api: FakeApi) -> None:
    api.on("POST", REMIND_PATH, REMIND_ACCEPTED)
    client = make_client(api)

    client.learners.remind(LEARNER_ID)
    client.learners.remind(LEARNER_ID)

    first, second = keys_sent(api, REMIND_PATH)
    assert first != second


def test_retries_reuse_the_same_key(api: FakeApi) -> None:
    api.on("POST", REMIND_PATH, UNAVAILABLE)
    api.on("POST", REMIND_PATH, network_error)
    api.on("POST", REMIND_PATH, REMIND_ACCEPTED)

    make_client(api).learners.remind(LEARNER_ID)

    keys = keys_sent(api, REMIND_PATH)
    assert len(keys) == 3
    assert len(set(keys)) == 1


def test_an_in_flight_duplicate_is_retried_with_the_same_key(api: FakeApi) -> None:
    api.on("POST", REMIND_PATH, problem(409, "conflict", detail="Request in flight"))
    api.on("POST", REMIND_PATH, REMIND_ACCEPTED)

    make_client(api).learners.remind(LEARNER_ID)

    first, second = keys_sent(api, REMIND_PATH)
    assert first == second


def test_a_caller_supplied_key_is_sent_as_is(api: FakeApi) -> None:
    api.on("POST", REMIND_PATH, UNAVAILABLE)
    api.on("POST", REMIND_PATH, REMIND_ACCEPTED)

    make_client(api).learners.remind(LEARNER_ID, idempotency_key="sync-2026-11-15-42")

    assert keys_sent(api, REMIND_PATH) == ["sync-2026-11-15-42"] * 2


def test_reusing_a_key_with_another_body_raises_the_idempotency_error(
    api: FakeApi,
) -> None:
    api.on("POST", REMIND_PATH, problem(422, "idempotency_key_reuse"))

    with pytest.raises(IdempotencyError):
        make_client(api).learners.remind(LEARNER_ID, idempotency_key="reused")

    assert len(keys_sent(api, REMIND_PATH)) == 1


def test_a_get_sends_no_idempotency_key(api: FakeApi) -> None:
    api.on("GET", LEARNER_PATH, Reply(json=LEARNER_JSON))

    make_client(api).learners.retrieve(LEARNER_ID)

    [request] = api.requests_to("GET", LEARNER_PATH)
    assert "idempotency-key" not in request.headers


def test_a_launch_link_is_retried_without_a_key(api: FakeApi) -> None:
    api.on("POST", LAUNCH_LINK_PATH, UNAVAILABLE)
    api.on("POST", LAUNCH_LINK_PATH, LAUNCH_LINK)

    link = make_client(api).learners.create_launch_link(LEARNER_ID)

    assert link.url == "https://training.teachmehipaa.com/launch/abc123"
    assert keys_sent(api, LAUNCH_LINK_PATH) == [None, None]


def test_a_patch_is_not_retried(api: FakeApi) -> None:
    api.on("PATCH", LEARNER_PATH, UNAVAILABLE)
    api.on("PATCH", LEARNER_PATH, Reply(json=LEARNER_JSON))

    with pytest.raises(APIError):
        make_client(api).learners.update(LEARNER_ID, if_match=ETAG, name="Ana Souza")

    [request] = api.requests_to("PATCH", LEARNER_PATH)
    assert "idempotency-key" not in request.headers
    assert request.headers["if-match"] == ETAG
    assert request.headers["content-type"] == "application/merge-patch+json"
    assert json.loads(request.content) == {"name": "Ana Souza"}


def test_a_patch_is_not_retried_after_a_network_error(api: FakeApi) -> None:
    api.on("PATCH", LEARNER_PATH, network_error)

    with pytest.raises(APIConnectionError):
        make_client(api).learners.update(LEARNER_ID, if_match=ETAG, name="Ana Souza")

    assert len(api.requests_to("PATCH", LEARNER_PATH)) == 1


async def test_async_retries_reuse_the_same_key(api: FakeApi) -> None:
    api.on("POST", REMIND_PATH, problem(429, "rate_limited"))
    api.on("POST", REMIND_PATH, REMIND_ACCEPTED)
    client = AsyncTeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.async_client(),
        sleep=FakeAsyncSleep(),
    )

    await client.learners.remind(LEARNER_ID)
    await client.learners.remind(LEARNER_ID, idempotency_key="given")

    first, retried, given = keys_sent(api, REMIND_PATH)
    assert first == retried
    assert given == "given"
