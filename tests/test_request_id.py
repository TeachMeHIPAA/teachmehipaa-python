"""A custom request id per call (story 50), through the public clients.

The API echoes an `x-request-id` it accepts (research `api-sdk-surface.md`
§7), so the id a caller sends comes back on `last_response` and on errors.
"""

from typing import Any

import httpx
import pytest

from teachmehipaa import AsyncTeachMeHipaa, NotFoundError, TeachMeHipaa
from tests.fake_api import (
    CLIENT_ID,
    CLIENT_SECRET,
    LEARNER_ID,
    LEARNER_JSON,
    ORG_ID,
    FakeApi,
    FakeAsyncSleep,
    FakeClock,
    FakeSleep,
    Reply,
    problem,
    token_json,
)

LEARNER_PATH = f"/organizations/{ORG_ID}/learners/{LEARNER_ID}"
EVENTS_PATH = f"/organizations/{ORG_ID}/events"
OPERATION_ID = "0b7d4a8e-5c1f-4e2a-9d3b-6f8a1c2e4b7d"
OPERATION_NAME = f"organizations/{ORG_ID}/operations/{OPERATION_ID}"
POLL_PATH = f"/organizations/{ORG_ID}/operations/{OPERATION_ID}"
SUBSCRIPTION_ID = "whs_01JD8K2M4N6P8R0T2V4X6Z8B0D"
TEST_DELIVERY_PATH = (
    f"/organizations/{ORG_ID}/webhook-subscriptions/{SUBSCRIPTION_ID}:test"
)
CUSTOM_ID = "hr-sync.2026-11-15.42"


def echoing(reply: Reply) -> Any:
    """Answers with `reply`, echoing the request's `x-request-id` as the API
    does."""

    def respond(request: httpx.Request) -> Reply:
        sent = request.headers.get("x-request-id")
        headers = {} if sent is None else {"x-request-id": sent}
        return Reply(
            status=reply.status,
            json=reply.json,
            content_type=reply.content_type,
            headers={**reply.headers, **headers},
        )

    return respond


@pytest.fixture
def api() -> FakeApi:
    fake = FakeApi()
    fake.on("POST", "/auth/token", Reply(json=token_json()))
    return fake


def sync_client(api: FakeApi, **options: Any) -> TeachMeHipaa:
    return TeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.sync_client(),
        **{"sleep": FakeSleep(), **options},
    )


def async_client(api: FakeApi, **options: Any) -> AsyncTeachMeHipaa:
    return AsyncTeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.async_client(),
        **{"sleep": FakeAsyncSleep(), **options},
    )


def sent_ids(api: FakeApi, method: str, path: str) -> list[str | None]:
    return [r.headers.get("x-request-id") for r in api.requests_to(method, path)]


def test_a_custom_request_id_is_sent_and_echoed_on_last_response(
    api: FakeApi,
) -> None:
    api.on("GET", LEARNER_PATH, echoing(Reply(json=LEARNER_JSON)))

    learner = sync_client(api).learners.retrieve(LEARNER_ID, request_id=CUSTOM_ID)

    assert sent_ids(api, "GET", LEARNER_PATH) == [CUSTOM_ID]
    assert learner.last_response.request_id == CUSTOM_ID


def test_without_a_request_id_none_is_sent(api: FakeApi) -> None:
    api.on("GET", LEARNER_PATH, Reply(json=LEARNER_JSON))

    sync_client(api).learners.retrieve(LEARNER_ID)

    assert sent_ids(api, "GET", LEARNER_PATH) == [None]


def test_every_retry_of_a_call_sends_the_same_request_id(api: FakeApi) -> None:
    api.on("GET", LEARNER_PATH, problem(503, "unavailable"))
    api.on("GET", LEARNER_PATH, echoing(Reply(json=LEARNER_JSON)))

    learner = sync_client(api).learners.retrieve(LEARNER_ID, request_id=CUSTOM_ID)

    assert sent_ids(api, "GET", LEARNER_PATH) == [CUSTOM_ID, CUSTOM_ID]
    assert learner.last_response.request_id == CUSTOM_ID


def test_an_error_carries_the_echoed_request_id(api: FakeApi) -> None:
    refused = problem(404, "not_found")
    api.on(
        "GET",
        LEARNER_PATH,
        echoing(
            Reply(status=404, json=refused.json, content_type=refused.content_type)
        ),
    )

    with pytest.raises(NotFoundError) as raised:
        sync_client(api).learners.retrieve(LEARNER_ID, request_id=CUSTOM_ID)

    assert raised.value.request_id == CUSTOM_ID


def test_the_request_id_is_not_sent_on_the_token_mint(api: FakeApi) -> None:
    api.on("GET", LEARNER_PATH, Reply(json=LEARNER_JSON))

    sync_client(api).learners.retrieve(LEARNER_ID, request_id=CUSTOM_ID)

    assert sent_ids(api, "POST", "/auth/token") == [None]


async def test_the_async_client_sends_and_echoes_the_request_id(
    api: FakeApi,
) -> None:
    api.on("GET", LEARNER_PATH, echoing(Reply(json=LEARNER_JSON)))

    learner = await async_client(api).learners.retrieve(
        LEARNER_ID, request_id=CUSTOM_ID
    )

    assert sent_ids(api, "GET", LEARNER_PATH) == [CUSTOM_ID]
    assert learner.last_response.request_id == CUSTOM_ID


def events_page(event_ids: list[str], next_cursor: str | None) -> Reply:
    items = [
        {
            "eventId": event_id,
            "eventType": "seat.consumed",
            "orgId": ORG_ID,
            "occurredAt": "2026-11-15T16:31:30.000Z",
            "data": {},
        }
        for event_id in event_ids
    ]
    return Reply(json={"items": items, "nextCursor": next_cursor})


def test_a_tail_sends_its_request_id_on_every_page(api: FakeApi) -> None:
    api.on("GET", EVENTS_PATH, events_page(["evt_01"], "evt_01"))
    api.on("GET", EVENTS_PATH, events_page(["evt_02"], None))

    events = list(sync_client(api).events.tail(request_id=CUSTOM_ID))

    assert [e.event_id for e in events] == ["evt_01", "evt_02"]
    assert sent_ids(api, "GET", EVENTS_PATH) == [CUSTOM_ID, CUSTOM_ID]


async def test_an_async_tail_sends_its_request_id(api: FakeApi) -> None:
    api.on("GET", EVENTS_PATH, events_page(["evt_01"], None))

    events = [e async for e in async_client(api).events.tail(request_id=CUSTOM_ID)]

    assert len(events) == 1
    assert sent_ids(api, "GET", EVENTS_PATH) == [CUSTOM_ID]


def test_wait_sends_its_request_id_on_every_poll(api: FakeApi) -> None:
    api.on(
        "POST", TEST_DELIVERY_PATH, Reply(202, {"name": OPERATION_NAME, "done": False})
    )
    api.on("GET", POLL_PATH, Reply(json={"name": OPERATION_NAME, "done": False}))
    api.on(
        "GET",
        POLL_PATH,
        echoing(
            Reply(
                json={
                    "name": OPERATION_NAME,
                    "done": True,
                    "response": {"_tag": "sent", "responseStatus": 200},
                }
            )
        ),
    )
    clock = FakeClock()
    client = sync_client(api, sleep=FakeSleep(clock), clock=clock)

    finished = client.webhook_subscriptions.test(SUBSCRIPTION_ID).wait(
        request_id=CUSTOM_ID
    )

    assert sent_ids(api, "GET", POLL_PATH) == [CUSTOM_ID, CUSTOM_ID]
    assert finished.last_response.request_id == CUSTOM_ID


async def test_async_wait_sends_its_request_id(api: FakeApi) -> None:
    api.on(
        "POST", TEST_DELIVERY_PATH, Reply(202, {"name": OPERATION_NAME, "done": False})
    )
    api.on(
        "GET",
        POLL_PATH,
        Reply(json={"name": OPERATION_NAME, "done": True, "response": None}),
    )
    clock = FakeClock()
    client = async_client(api, sleep=FakeAsyncSleep(clock), clock=clock)

    operation = await client.webhook_subscriptions.test(SUBSCRIPTION_ID)
    await operation.wait(request_id=CUSTOM_ID)

    assert sent_ids(api, "GET", POLL_PATH) == [CUSTOM_ID]
