"""Auto-paging lists and the Event log tail, through the public clients."""

import asyncio
import threading
from typing import Any

import pytest

from teachmehipaa import AsyncTeachMeHipaa, TeachMeHipaa
from tests.fake_api import (
    CLIENT_ID,
    CLIENT_SECRET,
    LEARNER_JSON,
    ORG_ID,
    FakeApi,
    FakeAsyncSleep,
    FakeSleep,
    Reply,
    token_json,
)

LEARNERS_PATH = f"/organizations/{ORG_ID}/learners"
EVENTS_PATH = f"/organizations/{ORG_ID}/events"


def learner(learner_id: str) -> dict[str, Any]:
    return {**LEARNER_JSON, "learnerId": learner_id}


def event(event_id: str) -> dict[str, Any]:
    """`dev#/components/schemas/Event`, a `learner.certified` envelope."""
    return {
        "eventId": event_id,
        "eventType": "learner.certified",
        "orgId": ORG_ID,
        "occurredAt": "2026-11-15T16:31:30.000Z",
        "data": {
            "learnerId": LEARNER_JSON["learnerId"],
            "email": LEARNER_JSON["email"],
            "externalId": LEARNER_JSON["externalId"],
            "courseId": "hipaa-2026",
            "status": "certified",
            "occurredAt": "2026-11-15T16:31:30.000Z",
        },
    }


def page(items: list[dict[str, Any]], next_cursor: str | None) -> Reply:
    """research `api-sdk-surface.md` §4: `{ items, nextCursor }`."""
    return Reply(json={"items": items, "nextCursor": next_cursor})


def scripted(path: str, *pages: Reply) -> FakeApi:
    api = FakeApi()
    api.on("POST", "/auth/token", Reply(json=token_json()))
    for reply in pages:
        api.on("GET", path, reply)
    return api


def queries(api: FakeApi, path: str) -> list[dict[str, str]]:
    return [dict(request.url.params) for request in api.requests_to("GET", path)]


def sync_client(api: FakeApi, sleep: FakeSleep | None = None) -> TeachMeHipaa:
    return TeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.sync_client(),
        sleep=sleep or FakeSleep(),
    )


def async_client(
    api: FakeApi, sleep: FakeAsyncSleep | None = None
) -> AsyncTeachMeHipaa:
    return AsyncTeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.async_client(),
        sleep=sleep or FakeAsyncSleep(),
    )


def after_params(api: FakeApi) -> list[str | None]:
    return [query.get("after") for query in queries(api, EVENTS_PATH)]


def test_iterating_a_list_follows_next_cursor_through_a_short_page_until_null() -> None:
    api = scripted(
        LEARNERS_PATH,
        page([learner("sub_1"), learner("sub_2")], "cur_2"),
        # Filters apply per page, so a page can be short with more to come.
        page([], "cur_3"),
        page([learner("sub_3")], None),
    )

    learner_ids = [item.learner_id for item in sync_client(api).learners.list(limit=2)]

    assert learner_ids == ["sub_1", "sub_2", "sub_3"]
    assert queries(api, LEARNERS_PATH) == [
        {"limit": "2"},
        {"limit": "2", "cursor": "cur_2"},
        {"limit": "2", "cursor": "cur_3"},
    ]


def test_breaking_out_of_the_loop_stops_fetching_pages() -> None:
    api = scripted(
        LEARNERS_PATH,
        page([learner("sub_1"), learner("sub_2")], "cur_2"),
        page([learner("sub_3"), learner("sub_4")], "cur_3"),
        page([learner("sub_5")], None),
    )

    learner_ids = []
    for item in sync_client(api).learners.list():
        learner_ids.append(item.learner_id)
        if item.learner_id == "sub_3":
            break

    assert learner_ids == ["sub_1", "sub_2", "sub_3"]
    assert len(api.requests_to("GET", LEARNERS_PATH)) == 2


def test_every_page_carries_the_first_calls_filters_and_limit_unvalidated() -> None:
    api = scripted(
        LEARNERS_PATH,
        page([learner("sub_1")], "cur_2"),
        page([learner("sub_2")], None),
    )

    # 500 is over the API's maximum of 100: the server, not the client,
    # rejects it.
    learners = sync_client(api).learners.list(
        limit=500, status="in_progress", course_id="hipaa-2026"
    )

    assert [item.learner_id for item in learners] == ["sub_1", "sub_2"]
    assert queries(api, LEARNERS_PATH) == [
        {"limit": "500", "status": "in_progress", "courseId": "hipaa-2026"},
        {
            "limit": "500",
            "status": "in_progress",
            "courseId": "hipaa-2026",
            "cursor": "cur_2",
        },
    ]


def test_the_event_log_pages_by_after_the_last_events_id_not_cursor() -> None:
    # §4: `nextCursor` is the last Event id while more rows exist.
    api = scripted(
        EVENTS_PATH,
        page([event("evt_01"), event("evt_02")], "evt_02"),
        page([event("evt_03")], None),
    )

    events = sync_client(api).events.list(type="learner.certified")

    assert [item.event_id for item in events] == ["evt_01", "evt_02", "evt_03"]
    assert queries(api, EVENTS_PATH) == [
        {"type": "learner.certified"},
        {"type": "learner.certified", "after": "evt_02"},
    ]


def test_the_event_log_resumes_after_the_last_event_even_if_next_cursor_differs() -> (
    None
):
    # The IR's `after` style keys on Event ids, so the last Event handed out
    # is the authoritative position, not the cursor's spelling of it.
    api = scripted(
        EVENTS_PATH,
        page([event("evt_01"), event("evt_02")], "evt_01"),
        page([event("evt_03")], None),
    )

    events = sync_client(api).events.list()

    assert [item.event_id for item in events] == ["evt_01", "evt_02", "evt_03"]
    assert queries(api, EVENTS_PATH) == [{}, {"after": "evt_02"}]


def test_the_event_log_falls_back_to_next_cursor_after_an_empty_page() -> None:
    api = scripted(
        EVENTS_PATH,
        page([], "evt_07"),
        page([event("evt_08")], None),
    )

    events = sync_client(api).events.list()

    assert [item.event_id for item in events] == ["evt_08"]
    assert queries(api, EVENTS_PATH) == [{}, {"after": "evt_07"}]


def test_a_list_returns_its_first_page_which_fetches_later_pages_on_request() -> None:
    api = scripted(
        LEARNERS_PATH,
        Reply(
            json={"items": [learner("sub_1")], "nextCursor": "cur_2"},
            headers={"x-request-id": "req_page_1"},
        ),
        page([learner("sub_2")], "cur_3"),
        page([learner("sub_3")], None),
    )

    first = sync_client(api).learners.list(limit=1)

    assert [item.learner_id for item in first.items] == ["sub_1"]
    assert first.next_cursor == "cur_2"
    assert first.last_response.request_id == "req_page_1"
    assert first.has_next_page()
    assert len(api.requests_to("GET", LEARNERS_PATH)) == 1

    second = first.get_next_page()
    assert [item.learner_id for item in second.items] == ["sub_2"]

    pages = [[item.learner_id for item in p.items] for p in second.iter_pages()]
    assert pages == [["sub_2"], ["sub_3"]]
    assert len(api.requests_to("GET", LEARNERS_PATH)) == 3


def test_get_next_page_on_the_last_page_raises_without_a_request() -> None:
    api = scripted(LEARNERS_PATH, page([learner("sub_1")], None))

    last = sync_client(api).learners.list()

    assert not last.has_next_page()
    with pytest.raises(RuntimeError, match="last page"):
        last.get_next_page()
    assert len(api.requests_to("GET", LEARNERS_PATH)) == 1


def test_auto_paging_iter_iterates_every_item_like_stripe() -> None:
    api = scripted(
        LEARNERS_PATH,
        page([learner("sub_1")], "cur_2"),
        page([learner("sub_2")], None),
    )

    learners = sync_client(api).learners.list().auto_paging_iter()

    assert [item.learner_id for item in learners] == ["sub_1", "sub_2"]


async def test_async_iteration_follows_next_cursor_through_a_short_page() -> None:
    api = scripted(
        LEARNERS_PATH,
        page([learner("sub_1"), learner("sub_2")], "cur_2"),
        page([], "cur_3"),
        page([learner("sub_3")], None),
    )

    # As in Stripe's library: await the call for the first page, then
    # `async for` over it for every item.
    learners = await async_client(api).learners.list(limit=2, status="in_progress")
    learner_ids = [item.learner_id async for item in learners]

    assert learner_ids == ["sub_1", "sub_2", "sub_3"]
    assert queries(api, LEARNERS_PATH) == [
        {"limit": "2", "status": "in_progress"},
        {"limit": "2", "status": "in_progress", "cursor": "cur_2"},
        {"limit": "2", "status": "in_progress", "cursor": "cur_3"},
    ]


async def test_breaking_out_of_an_async_loop_stops_fetching_pages() -> None:
    api = scripted(
        LEARNERS_PATH,
        page([learner("sub_1"), learner("sub_2")], "cur_2"),
        page([learner("sub_3"), learner("sub_4")], "cur_3"),
        page([learner("sub_5")], None),
    )

    learner_ids = []
    async for item in (await async_client(api).learners.list()).auto_paging_iter():
        learner_ids.append(item.learner_id)
        if item.learner_id == "sub_3":
            break

    assert learner_ids == ["sub_1", "sub_2", "sub_3"]
    assert len(api.requests_to("GET", LEARNERS_PATH)) == 2


async def test_the_async_event_log_pages_by_after() -> None:
    api = scripted(
        EVENTS_PATH,
        page([event("evt_01"), event("evt_02")], "evt_02"),
        page([event("evt_03")], None),
    )

    events = await async_client(api).events.list(type="learner.certified")

    assert [item.event_id async for item in events] == ["evt_01", "evt_02", "evt_03"]
    assert queries(api, EVENTS_PATH) == [
        {"type": "learner.certified"},
        {"type": "learner.certified", "after": "evt_02"},
    ]


async def test_an_async_page_fetches_later_pages_on_request() -> None:
    api = scripted(
        LEARNERS_PATH,
        page([learner("sub_1")], "cur_2"),
        page([learner("sub_2")], "cur_3"),
        page([learner("sub_3")], None),
    )

    first = await async_client(api).learners.list(limit=1)
    assert first.has_next_page()

    second = await first.get_next_page()
    pages = [p async for p in second.iter_pages()]

    assert [[item.learner_id for item in p.items] for p in pages] == [
        ["sub_2"],
        ["sub_3"],
    ]
    assert not pages[-1].has_next_page()
    with pytest.raises(RuntimeError, match="last page"):
        await pages[-1].get_next_page()
    assert len(api.requests_to("GET", LEARNERS_PATH)) == 3


def test_tail_resumes_from_an_event_id_and_returns_once_caught_up() -> None:
    sleep = FakeSleep()
    api = scripted(
        EVENTS_PATH,
        page([event("evt_03"), event("evt_04")], "evt_04"),
        # §4: `nextCursor` is null at the current end, so it gives no resume
        # point; the tail keeps the last id itself.
        page([event("evt_05")], None),
    )

    tail = sync_client(api, sleep).events.tail(
        after="evt_02", type="learner.certified", limit=2
    )
    assert tail.last_event_id == "evt_02"

    assert [item.event_id for item in tail] == ["evt_03", "evt_04", "evt_05"]
    assert tail.last_event_id == "evt_05"
    assert queries(api, EVENTS_PATH) == [
        {"limit": "2", "after": "evt_02", "type": "learner.certified"},
        {"limit": "2", "after": "evt_04", "type": "learner.certified"},
    ]
    assert sleep.waits == []


def test_tail_without_an_id_starts_at_the_oldest_retained_event() -> None:
    api = scripted(EVENTS_PATH, page([event("evt_01")], None))

    tail = sync_client(api).events.tail()
    assert tail.last_event_id is None

    assert [item.event_id for item in tail] == ["evt_01"]
    assert after_params(api) == [None]
    assert tail.last_event_id == "evt_01"


def test_following_tail_polls_from_its_last_id_every_2_seconds_until_stopped() -> None:
    sleep = FakeSleep()
    stop = threading.Event()
    api = scripted(
        EVENTS_PATH,
        page([event("evt_03")], None),
        page([], None),
        page([event("evt_04"), event("evt_05")], None),
    )

    tail = sync_client(api, sleep).events.tail(after="evt_02", follow=True, stop=stop)
    event_ids = []
    for item in tail:
        event_ids.append(item.event_id)
        if item.event_id == "evt_04":
            stop.set()

    # The stop lands mid-page: evt_05 was fetched but never handed out, so a
    # resume from last_event_id picks it up.
    assert event_ids == ["evt_03", "evt_04"]
    assert tail.last_event_id == "evt_04"
    assert after_params(api) == ["evt_02", "evt_03", "evt_03"]
    assert sleep.waits == [2.0, 2.0]


def test_following_tail_waits_the_interval_and_stops_polling_on_break() -> None:
    sleep = FakeSleep()
    api = scripted(EVENTS_PATH, page([], None), page([event("evt_03")], None))

    tail = sync_client(api, sleep).events.tail(
        after="evt_02", follow=True, interval=0.25
    )
    for item in tail:
        assert item.event_id == "evt_03"
        break

    assert after_params(api) == ["evt_02", "evt_02"]
    assert sleep.waits == [0.25]
    assert tail.last_event_id == "evt_03"


async def test_async_tail_resumes_from_an_event_id_and_returns_once_caught_up() -> None:
    sleep = FakeAsyncSleep()
    api = scripted(
        EVENTS_PATH,
        page([event("evt_03"), event("evt_04")], "evt_04"),
        page([event("evt_05")], None),
    )

    tail = async_client(api, sleep).events.tail(
        after="evt_02", type="learner.certified", limit=2
    )
    event_ids = [item.event_id async for item in tail]

    assert event_ids == ["evt_03", "evt_04", "evt_05"]
    assert tail.last_event_id == "evt_05"
    assert queries(api, EVENTS_PATH) == [
        {"limit": "2", "after": "evt_02", "type": "learner.certified"},
        {"limit": "2", "after": "evt_04", "type": "learner.certified"},
    ]
    assert sleep.waits == []


async def test_following_async_tail_polls_every_2_seconds_until_stopped() -> None:
    sleep = FakeAsyncSleep()
    stop = asyncio.Event()
    api = scripted(
        EVENTS_PATH,
        page([event("evt_03")], None),
        page([], None),
        page([event("evt_04"), event("evt_05")], None),
    )

    tail = async_client(api, sleep).events.tail(after="evt_02", follow=True, stop=stop)
    event_ids = []
    async for item in tail:
        event_ids.append(item.event_id)
        if item.event_id == "evt_04":
            stop.set()

    assert event_ids == ["evt_03", "evt_04"]
    assert tail.last_event_id == "evt_04"
    assert after_params(api) == ["evt_02", "evt_03", "evt_03"]
    assert sleep.waits == [2.0, 2.0]


async def test_async_tail_ends_mid_wait_when_stopped_between_polls() -> None:
    stop = asyncio.Event()

    async def sleep_forever(seconds: float) -> None:
        # A wait that never finishes on its own: only the stop can end it.
        stop.set()
        await asyncio.Future()

    api = scripted(EVENTS_PATH, page([event("evt_03")], None))
    client = AsyncTeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.async_client(),
        sleep=sleep_forever,
    )

    tail = client.events.tail(after="evt_02", follow=True, stop=stop)
    event_ids = [item.event_id async for item in tail]

    assert event_ids == ["evt_03"]
    assert len(api.requests_to("GET", EVENTS_PATH)) == 1
