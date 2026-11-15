from datetime import datetime, timezone

import pytest

from teachmehipaa import AsyncTeachMeHipaa, TeachMeHipaa, TeachMeHipaaError
from tests.fake_api import (
    ACCESS_TOKEN,
    CLIENT_ID,
    CLIENT_SECRET,
    ETAG,
    LEARNER_ID,
    LEARNER_JSON,
    ORG_ID,
    REQUEST_ID,
    FakeApi,
    Reply,
)

LEARNER_PATH = f"/organizations/{ORG_ID}/learners/{LEARNER_ID}"


def make_client(api: FakeApi) -> TeachMeHipaa:
    return TeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, http_client=api.sync_client()
    )


def test_client_retrieves_a_learner_by_id(api: FakeApi) -> None:
    learner = make_client(api).learners.retrieve(LEARNER_ID)

    assert learner.learner_id == LEARNER_ID
    assert learner.email == "ana@example.com"
    assert learner.name == "Ana Lima"
    assert learner.external_id == "hr-123"
    assert learner.status == "in_progress"
    assert learner.course.course_id == "hipaa-essentials"
    assert learner.course.title == "HIPAA Essentials"
    assert learner.started_at == datetime(2026, 11, 2, 10, 30, tzinfo=timezone.utc)
    assert learner.completed_at is None
    assert learner.certificate is None
    [request] = api.requests_to("GET", LEARNER_PATH)
    assert request.headers["authorization"] == f"Bearer {ACCESS_TOKEN}"
    assert request.headers["accept"] == "application/json"


async def test_async_client_retrieves_a_learner_by_id(api: FakeApi) -> None:
    client = AsyncTeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, http_client=api.async_client()
    )

    learner = await client.learners.retrieve(LEARNER_ID)

    assert learner.learner_id == LEARNER_ID
    assert learner.last_response.etag == ETAG
    [request] = api.requests_to("GET", LEARNER_PATH)
    assert request.headers["authorization"] == f"Bearer {ACCESS_TOKEN}"


def test_returned_learner_exposes_its_response_metadata(api: FakeApi) -> None:
    learner = make_client(api).learners.retrieve(LEARNER_ID)

    assert learner.last_response.status == 200
    assert learner.last_response.request_id == REQUEST_ID
    assert learner.last_response.etag == ETAG
    assert learner.last_response.headers["content-type"] == "application/json"


def test_passes_the_course_as_a_query_parameter(api: FakeApi) -> None:
    make_client(api).learners.retrieve(LEARNER_ID, course_id="hipaa-advanced")

    [request] = api.requests_to("GET", LEARNER_PATH)
    assert request.url.params["courseId"] == "hipaa-advanced"


def test_omits_the_course_when_not_given(api: FakeApi) -> None:
    make_client(api).learners.retrieve(LEARNER_ID)

    [request] = api.requests_to("GET", LEARNER_PATH)
    assert request.url.query == b""


def test_escapes_the_learner_id_in_the_path(api: FakeApi) -> None:
    api.on("GET", f"/organizations/{ORG_ID}/learners/a/b", Reply(json=LEARNER_JSON))

    make_client(api).learners.retrieve("a/b")

    assert api.requests[-1].url.raw_path == (
        f"/v1/organizations/{ORG_ID}/learners/a%2Fb".encode()
    )


def test_keeps_unknown_fields_and_new_status_values(api: FakeApi) -> None:
    api.replace(
        "GET",
        LEARNER_PATH,
        Reply(json={**LEARNER_JSON, "status": "on_leave", "department": "Billing"}),
    )

    learner = make_client(api).learners.retrieve(LEARNER_ID)

    assert learner.status == "on_leave"
    assert learner.model_extra == {"department": "Billing"}


def test_a_problem_response_raises_with_its_fields(api: FakeApi) -> None:
    api.replace(
        "GET",
        LEARNER_PATH,
        Reply(
            status=404,
            content_type="application/problem+json",
            json={
                "title": "Not Found",
                "status": 404,
                "code": "not_found",
                "detail": "No such learner.",
            },
            headers={"x-request-id": REQUEST_ID},
        ),
    )

    with pytest.raises(TeachMeHipaaError) as raised:
        make_client(api).learners.retrieve(LEARNER_ID)

    error = raised.value
    assert (error.status, error.code) == (404, "not_found")
    assert (error.title, error.detail) == ("Not Found", "No such learner.")
    assert error.request_id == REQUEST_ID
    assert error.headers["x-request-id"] == REQUEST_ID
    assert REQUEST_ID in str(error)
