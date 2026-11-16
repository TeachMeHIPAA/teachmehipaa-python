"""Operations: waiting for completion and reading export CSVs, through the
public clients."""

import asyncio
from typing import Any

import pytest

from teachmehipaa import (
    AsyncTeachMeHipaa,
    ExportResult,
    FieldError,
    OperationFailedError,
    OperationTimeoutError,
    TeachMeHipaa,
    TeachMeHipaaError,
    UnknownWebhookDeliveryResult,
    WebhookDeliveryFailed,
    WebhookDeliverySent,
    WebhookDeliverySettled,
    operation_id_from_name,
)
from tests.fake_api import (
    CLIENT_ID,
    CLIENT_SECRET,
    ORG_ID,
    FakeApi,
    FakeAsyncSleep,
    FakeClock,
    FakeSleep,
    Reply,
    token_json,
)

ORG = f"/organizations/{ORG_ID}"
OPERATION_ID = "0b7d4a8e-5c1f-4e2a-9d3b-6f8a1c2e4b7d"
# The Developer API names operations `organizations/{orgId}/operations/{id}`.
OPERATION_NAME = f"organizations/{ORG_ID}/operations/{OPERATION_ID}"
POLL_PATH = f"{ORG}/operations/{OPERATION_ID}"
SUBSCRIPTION_ID = "whs_01JD8K2M4N6P8R0T2V4X6Z8B0D"
TEST_DELIVERY_PATH = f"{ORG}/webhook-subscriptions/{SUBSCRIPTION_ID}:test"

# An export's 202: a done Operation whose `response` is the monorepo's
# `ExportArtifact` (`api-contracts` `bulk.schemas.ts`), the CSV in base64.
EXPORT_OPERATION: dict[str, Any] = {
    "name": OPERATION_NAME,
    "done": True,
    "metadata": {"kind": "enrollments:export"},
    "response": {
        "format": "csv",
        "contentType": "text/csv; charset=utf-8",
        "filename": f"enrollments-{ORG_ID}.csv",
        "rowCount": 2,
        "dataBase64": (
            "bGVhcm5lcklkLGVtYWlsLG5hbWUNCnN1Yl8wMUpEODBBQjJDM0Q0RTVGNkc3SDhKOUsw"
            "TSxhbmFAZXhhbXBsZS5jb20sIkV4YW1wbGUsIEFuYSINCnN1Yl8wMUpEODBBQjJDM0Q0"
            "RTVGNkc3SDhKOUswTixqb3NlQGV4YW1wbGUuY29tLEpvc8OpIE7DusOxZXoNCg=="
        ),
    },
}
# What `EXPORT_OPERATION`'s `dataBase64` decodes to: RFC 4180, CRLF, UTF-8.
EXPORTED_CSV = (
    "learnerId,email,name\r\n"
    'sub_01JD80AB2C3D4E5F6G7H8J9K0M,ana@example.com,"Example, Ana"\r\n'
    "sub_01JD80AB2C3D4E5F6G7H8J9K0N,jose@example.com,José Núñez\r\n"
)

# A Test delivery's 202: pending until the webhook worker settles it.
PENDING_OPERATION: dict[str, Any] = {"name": OPERATION_NAME, "done": False}
# The worker's settle on a 2xx from the endpoint (`response._tag`).
SENT_OPERATION: dict[str, Any] = {
    "name": OPERATION_NAME,
    "done": True,
    "response": {"_tag": "sent", "responseStatus": 200},
}

# `dev#/components/schemas/Operation`: a done Operation with a problem.
FAILED_OPERATION: dict[str, Any] = {
    "name": OPERATION_NAME,
    "done": True,
    "error": {
        "title": "Temporarily unavailable",
        "status": 503,
        "code": "temporarily_unavailable",
        "detail": "Webhook delivery is paused. Try again later.",
        "errors": [{"path": "url", "message": "unreachable"}],
    },
}


def scripted(*routes: tuple[str, str, Reply]) -> FakeApi:
    api = FakeApi()
    api.on("POST", "/auth/token", Reply(json=token_json()))
    for method, path, reply in routes:
        api.on(method, path, reply)
    return api


def sync_client(api: FakeApi, sleep: FakeSleep, clock: FakeClock) -> TeachMeHipaa:
    return TeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.sync_client(),
        clock=clock,
        sleep=sleep,
        max_retries=0,
    )


def async_client(
    api: FakeApi, sleep: FakeAsyncSleep, clock: FakeClock
) -> AsyncTeachMeHipaa:
    return AsyncTeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.async_client(),
        clock=clock,
        sleep=sleep,
        max_retries=0,
    )


def test_a_done_operation_returns_from_wait_without_a_request(
    clock: FakeClock,
) -> None:
    api = scripted(("POST", f"{ORG}/enrollments:export", Reply(202, EXPORT_OPERATION)))
    sleep = FakeSleep(clock)

    operation = sync_client(api, sleep, clock).enrollments.export(format="csv")
    finished = operation.wait()

    assert finished.done is True
    assert finished.name == OPERATION_NAME
    assert finished.last_response.status == 202
    assert len(api.requests) == 2
    assert sleep.waits == []


def test_a_pending_operation_polls_until_it_is_done(clock: FakeClock) -> None:
    api = scripted(
        ("POST", TEST_DELIVERY_PATH, Reply(202, PENDING_OPERATION)),
        ("GET", POLL_PATH, Reply(json=PENDING_OPERATION)),
        ("GET", POLL_PATH, Reply(json=PENDING_OPERATION)),
        (
            "GET",
            POLL_PATH,
            Reply(json=SENT_OPERATION, headers={"x-request-id": "req_poll_3"}),
        ),
    )
    sleep = FakeSleep(clock)
    client = sync_client(api, sleep, clock)

    operation = client.webhook_subscriptions.test(SUBSCRIPTION_ID)
    finished = operation.wait()

    assert operation.done is False
    assert finished.done is True
    assert finished.last_response.request_id == "req_poll_3"
    assert len(api.requests_to("GET", POLL_PATH)) == 3
    assert len(sleep.waits) == 3


def pending_then(*replies: Reply) -> FakeApi:
    """A Test delivery that starts pending, then polls through `replies`."""
    return scripted(
        ("POST", TEST_DELIVERY_PATH, Reply(202, PENDING_OPERATION)),
        *[("GET", POLL_PATH, reply) for reply in replies],
    )


def test_polls_back_off_from_one_second_doubling_with_jitter_to_a_ten_second_cap(
    clock: FakeClock,
) -> None:
    api = pending_then(*[Reply(json=PENDING_OPERATION)] * 7, Reply(json=SENT_OPERATION))
    sleep = FakeSleep(clock)

    sync_client(api, sleep, clock).webhook_subscriptions.test(SUBSCRIPTION_ID).wait()

    # Ceilings 1, 2, 4, 8, 10, 10, 10, 10 s; jitter keeps each within
    # 50-100 % of its ceiling, and never below the 1 s interval.
    ranges = [(1, 1), (1, 2), (2, 4), (4, 8), (5, 10), (5, 10), (5, 10), (5, 10)]
    assert len(sleep.waits) == len(ranges)
    for waited, (low, high) in zip(sleep.waits, ranges, strict=True):
        assert low <= waited <= high


def test_polls_start_from_the_interval_given(clock: FakeClock) -> None:
    api = pending_then(Reply(json=PENDING_OPERATION), Reply(json=SENT_OPERATION))
    sleep = FakeSleep(clock)

    operation = sync_client(api, sleep, clock).webhook_subscriptions.test(
        SUBSCRIPTION_ID
    )
    operation.wait(interval=0.25)

    assert sleep.waits[0] == 0.25
    assert 0.25 <= sleep.waits[1] <= 0.5


def test_wait_raises_operation_timeout_error_after_a_last_poll_at_the_deadline(
    clock: FakeClock,
) -> None:
    api = pending_then(Reply(json=PENDING_OPERATION))
    sleep = FakeSleep(clock)
    operation = sync_client(api, sleep, clock).webhook_subscriptions.test(
        SUBSCRIPTION_ID
    )

    with pytest.raises(OperationTimeoutError) as raised:
        operation.wait(timeout=5)

    assert isinstance(raised.value, TeachMeHipaaError)
    assert raised.value.message == f"Operation {OPERATION_NAME} was not done after 5 s"
    assert raised.value.operation.done is False
    assert raised.value.operation.name == OPERATION_NAME
    assert sum(sleep.waits) == pytest.approx(5)
    assert len(api.requests_to("GET", POLL_PATH)) == len(sleep.waits)


def test_wait_raises_operation_failed_error_with_the_problem(clock: FakeClock) -> None:
    api = pending_then(
        Reply(json=FAILED_OPERATION, headers={"x-request-id": "req_poll_1"})
    )
    operation = sync_client(api, FakeSleep(clock), clock).webhook_subscriptions.test(
        SUBSCRIPTION_ID
    )

    with pytest.raises(OperationFailedError) as raised:
        operation.wait()

    error = raised.value
    assert isinstance(error, TeachMeHipaaError)
    assert error.message == "Webhook delivery is paused. Try again later."
    assert error.status == 503
    assert error.code == "temporarily_unavailable"
    assert error.title == "Temporarily unavailable"
    assert error.detail == "Webhook delivery is paused. Try again later."
    assert error.errors == (FieldError(path="url", message="unreachable"),)
    assert error.request_id == "req_poll_1"
    assert error.operation.done is True


def test_an_operation_already_done_with_an_error_raises_without_a_request(
    clock: FakeClock,
) -> None:
    api = scripted(("POST", TEST_DELIVERY_PATH, Reply(202, FAILED_OPERATION)))
    operation = sync_client(api, FakeSleep(clock), clock).webhook_subscriptions.test(
        SUBSCRIPTION_ID
    )

    with pytest.raises(OperationFailedError):
        operation.wait()

    assert api.requests_to("GET", POLL_PATH) == []


async def test_async_a_done_operation_returns_from_wait_without_a_request(
    clock: FakeClock,
) -> None:
    api = scripted(("POST", f"{ORG}/enrollments:export", Reply(202, EXPORT_OPERATION)))
    sleep = FakeAsyncSleep(clock)

    client = async_client(api, sleep, clock)
    operation = await client.enrollments.export(format="csv")
    finished = await operation.wait()

    assert finished.done is True
    assert finished.last_response.status == 202
    assert len(api.requests) == 2
    assert sleep.waits == []


async def test_async_a_pending_operation_polls_with_backoff_until_it_is_done(
    clock: FakeClock,
) -> None:
    api = pending_then(
        *[Reply(json=PENDING_OPERATION)] * 3,
        Reply(json=SENT_OPERATION, headers={"x-request-id": "req_poll_4"}),
    )
    sleep = FakeAsyncSleep(clock)

    client = async_client(api, sleep, clock)
    operation = await client.webhook_subscriptions.test(SUBSCRIPTION_ID)
    finished = await operation.wait()

    assert operation.done is False
    assert finished.done is True
    assert finished.last_response.request_id == "req_poll_4"
    ranges = [(1, 1), (1, 2), (2, 4), (4, 8)]
    assert len(sleep.waits) == len(ranges)
    for waited, (low, high) in zip(sleep.waits, ranges, strict=True):
        assert low <= waited <= high


async def test_async_wait_raises_operation_timeout_error_at_the_deadline(
    clock: FakeClock,
) -> None:
    api = pending_then(Reply(json=PENDING_OPERATION))
    sleep = FakeAsyncSleep(clock)
    client = async_client(api, sleep, clock)
    operation = await client.webhook_subscriptions.test(SUBSCRIPTION_ID)

    with pytest.raises(OperationTimeoutError) as raised:
        await operation.wait(timeout=5)

    assert raised.value.operation.done is False
    assert sum(sleep.waits) == pytest.approx(5)
    assert len(api.requests_to("GET", POLL_PATH)) == len(sleep.waits)


async def test_async_wait_raises_operation_failed_error_with_the_problem(
    clock: FakeClock,
) -> None:
    api = pending_then(Reply(json=FAILED_OPERATION))
    client = async_client(api, FakeAsyncSleep(clock), clock)
    operation = await client.webhook_subscriptions.test(SUBSCRIPTION_ID)

    with pytest.raises(OperationFailedError) as raised:
        await operation.wait()

    assert raised.value.code == "temporarily_unavailable"
    assert raised.value.status == 503


async def test_cancelling_an_async_wait_stops_it_mid_sleep_without_a_poll() -> None:
    api = pending_then(Reply(json=SENT_OPERATION))
    waits: list[float] = []
    asleep = asyncio.Event()

    async def never_wakes(seconds: float) -> None:
        waits.append(seconds)
        asleep.set()
        await asyncio.Event().wait()

    client = AsyncTeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.async_client(),
        sleep=never_wakes,
    )
    operation = await client.webhook_subscriptions.test(SUBSCRIPTION_ID)

    waiting = asyncio.create_task(operation.wait())
    await asleep.wait()
    waiting.cancel()

    with pytest.raises(asyncio.CancelledError):
        await waiting
    assert waits == [1.0]
    assert api.requests_to("GET", POLL_PATH) == []


def test_export_result_returns_the_csv_text_file_name_and_row_count(
    clock: FakeClock,
) -> None:
    api = scripted(("POST", f"{ORG}/enrollments:export", Reply(202, EXPORT_OPERATION)))

    operation = sync_client(api, FakeSleep(clock), clock).enrollments.export(
        format="csv"
    )

    assert operation.export_result() == ExportResult(
        csv=EXPORTED_CSV, filename=f"enrollments-{ORG_ID}.csv", row_count=2
    )


@pytest.mark.parametrize("resource", ["certificates", "learners"])
def test_export_result_reads_every_export_the_same_way(
    resource: str, clock: FakeClock
) -> None:
    api = scripted(("POST", f"{ORG}/{resource}:export", Reply(202, EXPORT_OPERATION)))
    client = sync_client(api, FakeSleep(clock), clock)

    operation = (
        client.certificates.export(format="csv")
        if resource == "certificates"
        else client.learners.export(format="csv", course_id="hipaa-2026")
    )

    assert operation.export_result().csv == EXPORTED_CSV


def test_export_result_reads_an_export_retrieved_by_id(clock: FakeClock) -> None:
    api = scripted(("GET", POLL_PATH, Reply(json=EXPORT_OPERATION)))

    operation = sync_client(api, FakeSleep(clock), clock).operations.retrieve(
        OPERATION_ID
    )

    assert operation.export_result().csv == EXPORTED_CSV


async def test_async_export_result_returns_the_csv_text(clock: FakeClock) -> None:
    api = scripted(("POST", f"{ORG}/enrollments:export", Reply(202, EXPORT_OPERATION)))
    client = async_client(api, FakeAsyncSleep(clock), clock)

    operation = await client.enrollments.export(format="csv")

    assert operation.export_result().csv == EXPORTED_CSV


def test_export_result_refuses_an_operation_that_is_not_done(
    clock: FakeClock,
) -> None:
    api = scripted(("GET", POLL_PATH, Reply(json=PENDING_OPERATION)))
    operation = sync_client(api, FakeSleep(clock), clock).operations.retrieve(
        OPERATION_ID
    )

    with pytest.raises(ValueError, match="is not done; call wait\\(\\) first"):
        operation.export_result()


def test_export_result_refuses_an_operation_that_is_not_an_export(
    clock: FakeClock,
) -> None:
    api = scripted(("GET", POLL_PATH, Reply(json=SENT_OPERATION)))
    operation = sync_client(api, FakeSleep(clock), clock).operations.retrieve(
        OPERATION_ID
    )

    with pytest.raises(ValueError, match="did not produce a CSV export"):
        operation.export_result()


def test_export_result_raises_operation_failed_error_for_a_failed_export(
    clock: FakeClock,
) -> None:
    api = scripted(("GET", POLL_PATH, Reply(json=FAILED_OPERATION)))
    operation = sync_client(api, FakeSleep(clock), clock).operations.retrieve(
        OPERATION_ID
    )

    with pytest.raises(OperationFailedError):
        operation.export_result()


def test_a_test_delivery_operation_types_its_response_as_a_sent_delivery(
    clock: FakeClock,
) -> None:
    api = pending_then(Reply(json=SENT_OPERATION))
    client = sync_client(api, FakeSleep(clock), clock)

    finished = client.webhook_subscriptions.test(SUBSCRIPTION_ID).wait()

    assert isinstance(finished.response, WebhookDeliverySent)
    assert finished.response.tag == "sent"
    assert finished.response.response_status == 200


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (
            {"_tag": "failed", "reason": "endpoint_gone", "responseStatus": 410},
            WebhookDeliveryFailed(
                _tag="failed", reason="endpoint_gone", responseStatus=410
            ),
        ),
        (
            {"_tag": "failed", "reason": "connection_refused"},
            WebhookDeliveryFailed(_tag="failed", reason="connection_refused"),
        ),
        (
            {"_tag": "settled", "status": "delivered"},
            WebhookDeliverySettled(_tag="settled", status="delivered"),
        ),
    ],
)
def test_a_redrive_operation_types_each_delivery_result_by_tag(
    response: dict[str, Any], expected: object, clock: FakeClock
) -> None:
    redrive_path = f"{ORG}/webhook-subscriptions/{SUBSCRIPTION_ID}:redrive"
    done = {"name": OPERATION_NAME, "done": True, "response": response}
    api = scripted(("POST", redrive_path, Reply(202, done)))

    operation = sync_client(api, FakeSleep(clock), clock).webhook_subscriptions.redrive(
        SUBSCRIPTION_ID
    )

    assert operation.response == expected


async def test_a_delivery_result_with_an_unknown_tag_is_kept_not_rejected(
    clock: FakeClock,
) -> None:
    unknown = {"_tag": "skipped", "why": "nothing to deliver"}
    api = pending_then(
        Reply(json={"name": OPERATION_NAME, "done": True, "response": unknown})
    )
    client = async_client(api, FakeAsyncSleep(clock), clock)

    operation = await client.webhook_subscriptions.test(SUBSCRIPTION_ID)
    finished = await operation.wait()

    assert isinstance(finished.response, UnknownWebhookDeliveryResult)
    assert finished.response.tag == "skipped"
    assert finished.response.model_extra == {"why": "nothing to deliver"}


def test_operation_id_from_name_reads_the_id_that_operations_retrieve_takes() -> None:
    name = "organizations/org_acme/operations/0b7d4a8e-5c1f-4e2a-9d3b-6f8a1c2e4b7d"

    assert operation_id_from_name(name) == "0b7d4a8e-5c1f-4e2a-9d3b-6f8a1c2e4b7d"


@pytest.mark.parametrize(
    "name",
    [
        "0b7d4a8e-5c1f-4e2a-9d3b-6f8a1c2e4b7d",
        "organizations/org_acme/operations/",
        "organizations//operations/op_1",
        "organizations/org_acme/learners/sub_01JD80AB2C3D4E5F6G7H8J9K0M",
        "organizations/org_acme/operations/op_1/extra",
        "/organizations/org_acme/operations/op_1",
    ],
)
def test_operation_id_from_name_rejects_anything_but_an_operation_name(
    name: str,
) -> None:
    with pytest.raises(ValueError, match="is not an Operation name"):
        operation_id_from_name(name)
