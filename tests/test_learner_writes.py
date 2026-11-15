"""Learner updates as merge patches, and the write results of Learner create
and upsert, through the public client."""

import json
from typing import Any

import httpx
import pytest

from teachmehipaa import NOT_GIVEN, AsyncTeachMeHipaa, TeachMeHipaa
from tests.fake_api import (
    CLIENT_ID,
    CLIENT_SECRET,
    LEARNER_ID,
    LEARNER_JSON,
    LIVE_BASE,
    ORG_ID,
    FakeApi,
    FakeAsyncSleep,
    FakeSleep,
    Reply,
    token_json,
)

ORG = f"/organizations/{ORG_ID}"
LEARNER_PATH = f"{ORG}/learners/{LEARNER_ID}"
CREATE_PATH = f"{ORG}/learners"
UPSERT_PATH = f"{ORG}/learners/by-external-id/hr-123"
SUBSCRIPTION_ID = "whs_01JD8D"
SUBSCRIPTION_PATH = f"{ORG}/webhook-subscriptions/{SUBSCRIPTION_ID}"
ETAG = '"9f86d081"'

# `dev#/components/schemas/LearnerCreated` with `delivery: "none"`.
CREATED_JSON: dict[str, Any] = {
    **LEARNER_JSON,
    "status": "not_started",
    "startedAt": None,
    "delivery": "none",
    "joinUrl": "https://tme.so/j/7QX2",
}
SUBSCRIPTION_JSON: dict[str, Any] = {
    "subscriptionId": SUBSCRIPTION_ID,
    "endpointUrl": "https://hr.example.com/hooks/tmh",
    "eventTypes": ["learner.certified"],
    "enabled": True,
    "description": None,
    "seatsLowThreshold": 5,
    "secretKeyId": "whk_1",
    "createdAt": "2026-11-01T09:00:00Z",
    "rev": 4,
}


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


def sent_json(request: httpx.Request) -> Any:
    return json.loads(request.content)


# --- Merge patches --------------------------------------------------------


def test_a_learner_update_leaves_unset_fields_out_and_sends_null_to_clear(
    api: FakeApi,
) -> None:
    api.on("PATCH", LEARNER_PATH, Reply(json={**LEARNER_JSON, "externalId": None}))

    learner = make_client(api).learners.update(
        LEARNER_ID, if_match=ETAG, name=NOT_GIVEN, external_id=None
    )

    assert learner.external_id is None
    [request] = api.requests_to("PATCH", LEARNER_PATH)
    assert request.headers["content-type"] == "application/merge-patch+json"
    assert request.content == b'{"externalId": null}'


def test_a_learner_update_keeps_the_course_query_out_of_the_patch(
    api: FakeApi,
) -> None:
    api.on("PATCH", LEARNER_PATH, Reply(json=LEARNER_JSON))

    make_client(api).learners.update(
        LEARNER_ID, if_match=ETAG, name="Ana B. Example", course_id="hipaa-2026"
    )

    [request] = api.requests_to("PATCH", LEARNER_PATH)
    assert str(request.url) == f"{LIVE_BASE}{LEARNER_PATH}?courseId=hipaa-2026"
    assert sent_json(request) == {"name": "Ana B. Example"}


def test_a_subscription_update_sends_only_what_was_given(api: FakeApi) -> None:
    api.on("PATCH", SUBSCRIPTION_PATH, Reply(json=SUBSCRIPTION_JSON))

    make_client(api).webhook_subscriptions.update(
        SUBSCRIPTION_ID, if_match='"4"', endpoint_url=NOT_GIVEN, description=None
    )

    [request] = api.requests_to("PATCH", SUBSCRIPTION_PATH)
    assert request.headers["content-type"] == "application/merge-patch+json"
    assert sent_json(request) == {"description": None}


async def test_async_a_learner_update_sends_null_to_clear(api: FakeApi) -> None:
    api.on("PATCH", LEARNER_PATH, Reply(json=LEARNER_JSON))

    await make_async_client(api).learners.update(
        LEARNER_ID, if_match=ETAG, external_id=None
    )

    [request] = api.requests_to("PATCH", LEARNER_PATH)
    assert request.headers["content-type"] == "application/merge-patch+json"
    assert sent_json(request) == {"externalId": None}


# --- Learner write results ------------------------------------------------


def test_creating_a_learner_reports_created_with_its_delivery_details(
    api: FakeApi,
) -> None:
    api.on(
        "POST",
        CREATE_PATH,
        Reply(status=201, json=CREATED_JSON, headers={"etag": ETAG}),
    )

    result = make_client(api).learners.create(email="ana@example.com", delivery="none")

    assert result.created is True
    assert result.delivery == "none"
    assert result.join_url == "https://tme.so/j/7QX2"
    assert result.last_response.etag == ETAG
    [request] = api.requests_to("POST", CREATE_PATH)
    assert sent_json(request) == {"email": "ana@example.com", "delivery": "none"}
    assert request.headers["idempotency-key"]


def test_a_learner_already_there_is_not_created_and_has_no_delivery(
    api: FakeApi,
) -> None:
    api.on("POST", CREATE_PATH, Reply(status=200, json=LEARNER_JSON))

    result = make_client(api).learners.create(email="ana@example.com")

    assert result.created is False
    assert result.learner_id == LEARNER_ID
    assert (result.delivery, result.join_url) == (None, None)
    assert {"delivery", "join_url"}.isdisjoint(result.model_fields_set)


def test_a_replayed_upsert_is_told_apart_from_the_first(api: FakeApi) -> None:
    api.on("PUT", UPSERT_PATH, Reply(status=201, json=CREATED_JSON))
    api.on("PUT", UPSERT_PATH, Reply(status=200, json=LEARNER_JSON))
    client = make_client(api)

    first = client.learners.upsert_by_external_id(
        "hr-123", email="ana@example.com", delivery="none"
    )
    replay = client.learners.upsert_by_external_id(
        "hr-123", email="ana@example.com", delivery="none"
    )

    assert (first.created, first.join_url) == (True, "https://tme.so/j/7QX2")
    assert (replay.created, replay.join_url) == (False, None)


async def test_async_an_upsert_reports_created_on_201(api: FakeApi) -> None:
    api.on("PUT", UPSERT_PATH, Reply(status=201, json=CREATED_JSON))

    result = await make_async_client(api).learners.upsert_by_external_id(
        "hr-123", email="ana@example.com"
    )

    assert result.created is True
    assert result.delivery == "none"
