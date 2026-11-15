import logging

import pytest

from teachmehipaa import AsyncTeachMeHipaa, NotFoundError, TeachMeHipaa
from tests.fake_api import (
    ACCESS_TOKEN,
    CLIENT_ID,
    CLIENT_SECRET,
    LEARNER_ID,
    ORG_ID,
    REQUEST_ID,
    FakeApi,
    problem,
)

LEARNERS_PATH = f"/organizations/{ORG_ID}/learners"


def _records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == "teachmehipaa"]


def _fields(record: logging.LogRecord) -> dict[str, object]:
    return {
        name: getattr(record, name)
        for name in ("method", "path", "status", "request_id")
    }


def test_the_library_logs_nothing_unless_debug_logging_is_on(
    api: FakeApi, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    client = TeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, http_client=api.sync_client()
    )

    client.learners.retrieve(LEARNER_ID)

    assert _records(caplog) == []


def test_each_response_logs_method_path_status_and_request_id(
    api: FakeApi, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="teachmehipaa")
    client = TeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, http_client=api.sync_client()
    )

    client.learners.retrieve(LEARNER_ID)

    records = _records(caplog)
    assert [_fields(r) for r in records] == [
        {
            "method": "POST",
            "path": "/v1/auth/token",
            "status": 200,
            "request_id": None,
        },
        {
            "method": "GET",
            "path": "/v1/auth/introspection",
            "status": 200,
            "request_id": None,
        },
        {
            "method": "GET",
            "path": f"/v1{LEARNERS_PATH}/{LEARNER_ID}",
            "status": 200,
            "request_id": REQUEST_ID,
        },
    ]
    assert all(r.levelno == logging.DEBUG for r in records)
    latencies = [r.__dict__["latency_ms"] for r in records]
    assert all(isinstance(ms, float) and ms >= 0 for ms in latencies)


def test_logs_leave_out_query_strings_bodies_and_credentials(
    api: FakeApi, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="teachmehipaa")
    api.on(
        "GET",
        LEARNERS_PATH,
        problem(404, "not_found", detail="No learner ana@example.com"),
    )
    client = TeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, http_client=api.sync_client()
    )

    with pytest.raises(NotFoundError):
        client.learners.list(email="ana@example.com")

    [*_, listing] = _records(caplog)
    assert _fields(listing) == {
        "method": "GET",
        "path": f"/v1{LEARNERS_PATH}",
        "status": 404,
        "request_id": REQUEST_ID,
    }
    logged = caplog.text
    for secret in ("ana@example.com", ACCESS_TOKEN, CLIENT_SECRET, "not_found"):
        assert secret not in logged


async def test_the_async_client_logs_each_response(
    api: FakeApi, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="teachmehipaa")
    client = AsyncTeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, http_client=api.async_client()
    )

    await client.learners.retrieve(LEARNER_ID)

    assert [_fields(r)["path"] for r in _records(caplog)] == [
        "/v1/auth/token",
        "/v1/auth/introspection",
        f"/v1{LEARNERS_PATH}/{LEARNER_ID}",
    ]
