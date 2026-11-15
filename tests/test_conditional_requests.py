"""Conditional writes (`If-Match`) and reads (`If-None-Match`), through the
public client."""

from typing import Any

import pytest

from teachmehipaa import (
    AsyncTeachMeHipaa,
    NotModified,
    PreconditionFailedError,
    TeachMeHipaa,
)
from teachmehipaa.types import Course
from tests.fake_api import (
    CLIENT_ID,
    CLIENT_SECRET,
    LEARNER_ID,
    LEARNER_JSON,
    ORG_ID,
    FakeApi,
    FakeAsyncSleep,
    FakeSleep,
    Reply,
    problem,
    token_json,
)

LEARNER_PATH = f"/organizations/{ORG_ID}/learners/{LEARNER_ID}"
SUBSCRIPTION_ID = "whs_01JD8D"
SUBSCRIPTION_PATH = f"/organizations/{ORG_ID}/webhook-subscriptions/{SUBSCRIPTION_ID}"
OFFBOARD_PATH = f"{LEARNER_PATH}:offboard"

# Learners carry a quoted SHA-256 hex strong tag (api-sdk-surface.md §5).
LEARNER_ETAG = '"9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"'
# Rev-based resources carry a quoted revision.
COURSE_ETAG = '"7"'
COURSE_ID = "hipaa-2026"
COURSE_PATH = f"/courses/{COURSE_ID}"
# `dev#/components/schemas/CourseDto`.
COURSE_JSON: dict[str, Any] = {
    "courseId": COURSE_ID,
    "title": "HIPAA Training 2026",
    "courseVersion": "2026.1",
    "passingThreshold": 80,
}
SUBSCRIPTION_JSON: dict[str, Any] = {
    "subscriptionId": SUBSCRIPTION_ID,
    "endpointUrl": "https://hr.example.com/hooks/tmh",
    "eventTypes": ["learner.certified"],
    "enabled": False,
    "description": None,
    "seatsLowThreshold": 5,
    "secretKeyId": "whk_1",
    "createdAt": "2026-11-01T09:00:00Z",
    "rev": 4,
}

# As `conditional.core.ts` sends them.
PRECONDITION_FAILED = problem(
    412,
    "precondition_failed",
    title="Precondition failed",
    detail="The resource has changed since you read it.",
)
PRECONDITION_REQUIRED = problem(
    428,
    "precondition_required",
    title="Precondition required",
    detail="Send If-Match with the resource's current ETag.",
)


@pytest.fixture
def api() -> FakeApi:
    fake = FakeApi()
    fake.on("POST", "/auth/token", Reply(json=token_json()))
    return fake


def make_client(api: FakeApi) -> TeachMeHipaa:
    return TeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.sync_client(),
        sleep=FakeSleep(),
    )


def make_async_client(api: FakeApi) -> AsyncTeachMeHipaa:
    return AsyncTeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.async_client(),
        sleep=FakeAsyncSleep(),
    )


# --- Conditional writes ---------------------------------------------------


def test_if_match_sends_the_etag_on_a_learner_update(api: FakeApi) -> None:
    api.on("PATCH", LEARNER_PATH, Reply(json=LEARNER_JSON, headers={"etag": '"next"'}))

    learner = make_client(api).learners.update(
        LEARNER_ID, if_match=LEARNER_ETAG, name="Ana Example"
    )

    assert learner.last_response.etag == '"next"'
    [request] = api.requests_to("PATCH", LEARNER_PATH)
    assert request.headers["if-match"] == LEARNER_ETAG


def test_if_match_takes_the_etag_from_a_learner_it_returned(api: FakeApi) -> None:
    api.on(
        "GET", LEARNER_PATH, Reply(json=LEARNER_JSON, headers={"etag": LEARNER_ETAG})
    )
    api.on("PATCH", LEARNER_PATH, Reply(json=LEARNER_JSON))
    client = make_client(api)

    learner = client.learners.retrieve(LEARNER_ID)
    client.learners.update(LEARNER_ID, if_match=learner, external_id=None)

    [request] = api.requests_to("PATCH", LEARNER_PATH)
    assert request.headers["if-match"] == LEARNER_ETAG


def test_an_object_without_an_etag_is_refused_before_sending(api: FakeApi) -> None:
    api.on("GET", LEARNER_PATH, Reply(json=LEARNER_JSON))
    client = make_client(api)
    learner = client.learners.retrieve(LEARNER_ID)

    with pytest.raises(ValueError, match="ETag"):
        client.learners.offboard(LEARNER_ID, if_match=learner)

    assert api.requests_to("POST", OFFBOARD_PATH) == []


def test_an_optional_if_match_is_left_out_when_not_given(api: FakeApi) -> None:
    api.on("POST", OFFBOARD_PATH, Reply(json=LEARNER_JSON))

    make_client(api).learners.offboard(LEARNER_ID)

    [request] = api.requests_to("POST", OFFBOARD_PATH)
    assert "if-match" not in request.headers


def test_a_stale_etag_raises_precondition_failed(api: FakeApi) -> None:
    api.on("PATCH", LEARNER_PATH, PRECONDITION_FAILED)

    with pytest.raises(PreconditionFailedError) as raised:
        make_client(api).learners.update(
            LEARNER_ID, if_match=LEARNER_ETAG, name="Ana Example"
        )

    assert (raised.value.status, raised.value.code) == (412, "precondition_failed")
    # A PATCH is never retried.
    assert len(api.requests_to("PATCH", LEARNER_PATH)) == 1


def test_a_precondition_required_answer_raises_precondition_failed(
    api: FakeApi,
) -> None:
    api.on("PATCH", SUBSCRIPTION_PATH, PRECONDITION_REQUIRED)

    with pytest.raises(PreconditionFailedError) as raised:
        make_client(api).webhook_subscriptions.update(
            SUBSCRIPTION_ID, if_match="*", enabled=False
        )

    assert (raised.value.status, raised.value.code) == (428, "precondition_required")


async def test_async_if_match_takes_the_etag_from_a_returned_subscription(
    api: FakeApi,
) -> None:
    api.on(
        "GET",
        SUBSCRIPTION_PATH,
        Reply(json=SUBSCRIPTION_JSON, headers={"etag": '"4"'}),
    )
    api.on("PATCH", SUBSCRIPTION_PATH, Reply(json=SUBSCRIPTION_JSON))
    client = make_async_client(api)

    subscription = await client.webhook_subscriptions.retrieve(SUBSCRIPTION_ID)
    await client.webhook_subscriptions.update(
        SUBSCRIPTION_ID, if_match=subscription, enabled=False
    )

    [request] = api.requests_to("PATCH", SUBSCRIPTION_PATH)
    assert request.headers["if-match"] == '"4"'


# --- Conditional reads ----------------------------------------------------


def test_a_current_copy_comes_back_as_not_modified(api: FakeApi) -> None:
    api.on(
        "GET",
        COURSE_PATH,
        Reply(
            status=304,
            text="",
            content_type="text/plain",
            headers={"etag": COURSE_ETAG, "x-request-id": "req_304"},
        ),
    )

    result = make_client(api).courses.retrieve(COURSE_ID, if_none_match=COURSE_ETAG)

    assert isinstance(result, NotModified)
    assert not result
    assert result.last_response.status == 304
    assert result.last_response.etag == COURSE_ETAG
    assert result.last_response.request_id == "req_304"
    [request] = api.requests_to("GET", COURSE_PATH)
    assert request.headers["if-none-match"] == COURSE_ETAG


def test_a_changed_object_is_returned_using_the_held_copys_etag(
    api: FakeApi,
) -> None:
    api.on("GET", COURSE_PATH, Reply(json=COURSE_JSON, headers={"etag": COURSE_ETAG}))
    api.on(
        "GET",
        COURSE_PATH,
        Reply(json={**COURSE_JSON, "courseVersion": "2026.2"}, headers={"etag": '"8"'}),
    )
    client = make_client(api)
    cached = client.courses.retrieve(COURSE_ID)

    current = client.courses.retrieve(COURSE_ID, if_none_match=cached) or cached

    assert current.course_version == "2026.2"
    assert api.requests_to("GET", COURSE_PATH)[1].headers["if-none-match"] == (
        COURSE_ETAG
    )


def test_a_plain_retrieve_is_typed_as_the_object_alone(api: FakeApi) -> None:
    api.on("GET", COURSE_PATH, Reply(json=COURSE_JSON))

    # mypy checks this annotation against the overload without If-None-Match.
    course: Course = make_client(api).courses.retrieve(COURSE_ID, timeout=5)

    assert course.title == "HIPAA Training 2026"
    [request] = api.requests_to("GET", COURSE_PATH)
    assert "if-none-match" not in request.headers


async def test_async_a_current_subscription_comes_back_as_not_modified(
    api: FakeApi,
) -> None:
    api.on(
        "GET",
        SUBSCRIPTION_PATH,
        Reply(status=304, text="", content_type="text/plain", headers={"etag": '"4"'}),
    )

    result = await make_async_client(api).webhook_subscriptions.retrieve(
        SUBSCRIPTION_ID, if_none_match='"4"'
    )

    assert isinstance(result, NotModified)
    assert result.last_response.etag == '"4"'
