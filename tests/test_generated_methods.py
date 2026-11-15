"""Representative generated methods, exercised through the public client:
one per response kind and per request shape the IR describes."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest

from teachmehipaa import APIConnectionError, AsyncTeachMeHipaa, SyncPage, TeachMeHipaa
from teachmehipaa.types import (
    AuditEventActorUser,
    AuditEventMemberRemoved,
    Enrollment,
    EnrollmentCancelRefunded,
    UnknownAuditEvent,
    UnknownAuditEventActor,
)
from tests.fake_api import (
    CLIENT_ID,
    CLIENT_SECRET,
    ETAG,
    LEARNER_JSON,
    ORG_ID,
    REQUEST_ID,
    FakeApi,
    FakeAsyncSleep,
    FakeSleep,
    Reply,
    network_error,
    token_json,
)

PARTNER_ID = "ptn_01JD8Z4N3QX5V7W9Y2B4C6D8EH"
ENROLLMENT_ID = "enr_01JD8Z4N3QX5V7W9Y2B4C6D8EJ"
SUBSCRIPTION_ID = "whs_01JD8Z4N3QX5V7W9Y2B4C6D8EK"
CERTIFICATE_ID = "cert_01JD8Z4N3QX5V7W9Y2B4C6D8EM"

ENROLLMENT_JSON: dict[str, Any] = {
    "enrollmentId": ENROLLMENT_ID,
    "subjectId": "sub_01JD8Z4N3QX5V7W9Y2B4C6D8EG",
    "courseId": "hipaa-essentials",
    "orgId": ORG_ID,
    "status": "CANCELLED",
    "effectiveStatus": "CANCELLED",
    "archived": False,
    "cycle": 1,
    "rev": 4,
    "invitedAt": "2026-11-01T09:00:00Z",
    "startedAt": None,
    "completedAt": None,
    "certifiedAt": None,
    "expiresAt": None,
    "certificateId": None,
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
    "rev": 3,
}
ACTOR = {"type": "user", "subjectId": "sub_admin"}
MEMBER_REMOVED = {
    "eventId": "aud_1",
    "at": "2026-11-10T08:00:00Z",
    "type": "member.removed",
    "actorSubjectId": "sub_admin",
    "actor": ACTOR,
    "subjectId": "sub_gone",
    "wasAdmin": False,
}


@pytest.fixture
def api() -> FakeApi:
    fake = FakeApi()
    fake.on("POST", "/auth/token", Reply(json=token_json()))
    return fake


def make_client(api: FakeApi, **options: Any) -> TeachMeHipaa:
    return TeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.sync_client(),
        sleep=FakeSleep(),
        **options,
    )


def org(path: str) -> str:
    return f"/organizations/{ORG_ID}{path}"


def sent_json(request: httpx.Request) -> Any:
    return json.loads(request.content)


# --- Custom methods and idempotency ---------------------------------------


def test_cancelling_an_enrollment_posts_the_custom_method_with_a_key(
    api: FakeApi,
) -> None:
    path = org(f"/enrollments/{ENROLLMENT_ID}:cancel")
    api.on("POST", path, Reply(json=ENROLLMENT_JSON))

    enrollment = make_client(api).enrollments.cancel(ENROLLMENT_ID)

    assert isinstance(enrollment, Enrollment)
    assert enrollment.enrollment_id == ENROLLMENT_ID
    [request] = api.requests_to("POST", path)
    assert request.url.raw_path == (
        f"/v1/organizations/{ORG_ID}/enrollments/{ENROLLMENT_ID}:cancel".encode()
    )
    assert uuid.UUID(request.headers["idempotency-key"]).version == 4
    assert sent_json(request) == {}


def test_a_refunded_cancel_returns_the_refund(api: FakeApi) -> None:
    path = org(f"/enrollments/{ENROLLMENT_ID}:cancel")
    refund = {"refundId": "re_1", "amountCents": 2500, "currency": "usd"}
    api.on("POST", path, Reply(json={**ENROLLMENT_JSON, "refund": refund}))

    enrollment = make_client(api).enrollments.cancel(
        ENROLLMENT_ID, refund=True, idempotency_key="cancel-42"
    )

    assert isinstance(enrollment, EnrollmentCancelRefunded)
    assert enrollment.refund.amount_cents == 2500
    assert enrollment.last_response.status == 200
    [request] = api.requests_to("POST", path)
    assert request.headers["idempotency-key"] == "cancel-42"
    assert sent_json(request) == {"refund": True}


def test_a_batch_by_ids_sends_the_selected_ids(api: FakeApi) -> None:
    path = org("/enrollments:batch")
    api.on(
        "POST",
        path,
        Reply(
            json={
                "operation": "remind",
                "results": [{"enrollmentId": ENROLLMENT_ID, "outcome": "succeeded"}],
            }
        ),
    )

    results = make_client(api).enrollments.batch(
        operation="remind", select={"enrollment_ids": [ENROLLMENT_ID]}
    )

    assert results.results[0].outcome == "succeeded"
    [request] = api.requests_to("POST", path)
    assert sent_json(request) == {
        "operation": "remind",
        "select": {"enrollmentIds": [ENROLLMENT_ID]},
    }


def test_nested_params_are_sent_in_camel_case(api: FakeApi) -> None:
    path = org("/seat-orders")
    api.on(
        "POST",
        path,
        Reply(
            status=201,
            json={
                "seatOrderId": "so_1",
                "status": "requires_action",
                "nextAction": {"type": "redirect", "url": "https://pay.example/so_1"},
                "failure": None,
            },
        ),
    )

    order = make_client(api).seat_orders.create(
        quantity=5,
        payment={
            "method": "hosted_checkout",
            "return_url": "https://hr.example.com/billing/done",
        },
        client_reference="po-889",
    )

    assert order.next_action is not None
    assert order.next_action.type == "redirect"
    [request] = api.requests_to("POST", path)
    assert sent_json(request) == {
        "quantity": 5,
        "payment": {
            "method": "hosted_checkout",
            "returnUrl": "https://hr.example.com/billing/done",
        },
        "clientReference": "po-889",
    }


# --- Retry safety ------------------------------------------------------------


def test_a_caller_key_does_not_make_a_delete_retryable(api: FakeApi) -> None:
    # No generated PATCH or DELETE takes a key, so drive the pipeline the
    # generated methods use with one that does.
    from teachmehipaa._core._request import ApiRequest, RequestOptions

    path = org(f"/webhook-subscriptions/{SUBSCRIPTION_ID}")
    api.on("DELETE", path, network_error)
    client = make_client(api)

    with pytest.raises(APIConnectionError):
        client.webhook_subscriptions._pipeline.request_empty(
            ApiRequest(
                "DELETE",
                "/organizations/{orgId}/webhook-subscriptions/{id}",
                path_params={"id": SUBSCRIPTION_ID},
                org_scoped=True,
                options=RequestOptions(idempotency_key="delete-1"),
            )
        )

    assert len(api.requests_to("DELETE", path)) == 1


# --- Partner methods ------------------------------------------------------


def test_partner_organizations_are_listed_by_partner_id(api: FakeApi) -> None:
    path = f"/partners/{PARTNER_ID}/organizations"
    api.on(
        "GET",
        path,
        Reply(
            json={
                "items": [
                    {
                        "orgId": "org_child",
                        "name": "Child Clinic",
                        "createdAt": "2026-10-01T00:00:00Z",
                        "grantActive": True,
                    }
                ],
                "nextCursor": "c_2",
            },
            headers={"x-request-id": REQUEST_ID},
        ),
    )
    client = TeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, http_client=api.sync_client()
    )

    page = client.partners.organizations.list(PARTNER_ID, limit=10)

    assert isinstance(page, SyncPage)
    assert [o.org_id for o in page.items] == ["org_child"]
    assert page.items[0].created_at == datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert page.next_cursor == "c_2"
    assert page.last_response.request_id == REQUEST_ID
    [request] = api.requests_to("GET", path)
    assert request.url.params["limit"] == "10"
    # Partner methods never resolve the Organization binding.
    assert api.requests_to("GET", "/auth/introspection") == []


def test_creating_a_partner_organization_returns_its_refresh_token(
    api: FakeApi,
) -> None:
    path = f"/partners/{PARTNER_ID}/organizations"
    api.on(
        "POST",
        path,
        Reply(
            status=201,
            json={
                "orgId": "org_child",
                "name": "Child Clinic",
                "createdAt": "2026-10-01T00:00:00Z",
                "grant": {"grantId": "grt_1", "scopes": ["learners:read"]},
                "refresh_token": "tmh_rt_secret",
            },
        ),
    )
    client = TeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, http_client=api.sync_client()
    )

    created = client.partners.organizations.create(
        PARTNER_ID,
        name="Child Clinic",
        admin_email="admin@child.example",
        scopes=["learners:read"],
    )

    assert created.refresh_token == "tmh_rt_secret"
    assert created.grant.scopes == ["learners:read"]
    [request] = api.requests_to("POST", path)
    assert "idempotency-key" in request.headers
    assert sent_json(request) == {
        "name": "Child Clinic",
        "adminEmail": "admin@child.example",
        "scopes": ["learners:read"],
    }


# --- PATCH and DELETE -----------------------------------------------------


def test_an_update_sends_merge_patch_with_explicit_nulls_only(api: FakeApi) -> None:
    path = org(f"/webhook-subscriptions/{SUBSCRIPTION_ID}")
    api.on("PATCH", path, Reply(json={**SUBSCRIPTION_JSON, "enabled": False}))

    subscription = make_client(api).webhook_subscriptions.update(
        SUBSCRIPTION_ID, if_match=ETAG, enabled=False, description=None
    )

    assert subscription.enabled is False
    [request] = api.requests_to("PATCH", path)
    assert request.headers["content-type"] == "application/merge-patch+json"
    assert request.headers["if-match"] == ETAG
    assert "idempotency-key" not in request.headers
    assert sent_json(request) == {"enabled": False, "description": None}


def test_deleting_a_subscription_succeeds_on_204(api: FakeApi) -> None:
    path = org(f"/webhook-subscriptions/{SUBSCRIPTION_ID}")
    api.on("DELETE", path, Reply(status=204, text="", content_type="text/plain"))

    # Returns None, which the signature already promises the type checker.
    make_client(api).webhook_subscriptions.delete(SUBSCRIPTION_ID)

    [request] = api.requests_to("DELETE", path)
    assert request.content == b""


async def test_async_delete_succeeds_on_204(api: FakeApi) -> None:
    path = org("/billing/payment-method")
    api.on("DELETE", path, Reply(status=204, text="", content_type="text/plain"))
    client = AsyncTeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.async_client(),
        sleep=FakeAsyncSleep(),
    )

    await client.payment_method.delete()

    assert len(api.requests_to("DELETE", path)) == 1


# --- Learner write results ------------------------------------------------


@pytest.mark.parametrize(("status", "created"), [(201, True), (200, False)])
def test_an_upsert_reports_whether_it_created_the_learner(
    api: FakeApi, status: int, created: bool
) -> None:
    path = org("/learners/by-external-id/hr-123")
    body = dict(LEARNER_JSON)
    if status == 201:
        body |= {"delivery": "none", "joinUrl": "https://tme.so/j/abc"}
    api.on("PUT", path, Reply(status=status, json=body))

    result = make_client(api).learners.upsert_by_external_id(
        "hr-123", email="ana@example.com", delivery="none"
    )

    assert result.created is created
    assert result.external_id == "hr-123"
    assert result.join_url == ("https://tme.so/j/abc" if created else None)
    [request] = api.requests_to("PUT", path)
    assert sent_json(request) == {"email": "ana@example.com", "delivery": "none"}


# --- Tolerant models ------------------------------------------------------


def test_unknown_enum_values_and_fields_are_kept_on_nested_models(
    api: FakeApi,
) -> None:
    path = org("/members/sub_new")
    api.on(
        "GET",
        path,
        Reply(
            json={
                "subjectId": "sub_new",
                "email": "ops@example.com",
                "name": None,
                "role": "auditor",
                "isDisabled": False,
                "department": "Compliance",
            }
        ),
    )

    member = make_client(api).members.retrieve("sub_new")

    assert member.role == "auditor"
    assert member.model_extra == {"department": "Compliance"}


def test_unknown_union_variants_parse_instead_of_raising(api: FakeApi) -> None:
    path = org("/audit-events")
    from_the_future = {
        "eventId": "aud_2",
        "at": "2026-11-11T08:00:00Z",
        "type": "course.retired",
        "actor": {"type": "robot", "robotId": "rbt_1"},
        "courseId": "hipaa-2019",
    }
    api.on(
        "GET",
        path,
        Reply(json={"items": [MEMBER_REMOVED, from_the_future], "nextCursor": None}),
    )

    page = make_client(api).audit_events.list(
        since=datetime(2026, 11, 1, tzinfo=timezone.utc)
    )

    known, unknown = page.items
    assert isinstance(known, AuditEventMemberRemoved)
    assert isinstance(known.actor, AuditEventActorUser)
    assert known.actor.subject_id == "sub_admin"
    assert isinstance(unknown, UnknownAuditEvent)
    assert unknown.type == "course.retired"
    assert unknown.model_extra is not None
    assert unknown.model_extra["courseId"] == "hipaa-2019"
    assert page.next_cursor is None
    [request] = api.requests_to("GET", path)
    assert request.url.params["since"] == "2026-11-01T00:00:00Z"


def test_an_unknown_nested_variant_falls_back_too(api: FakeApi) -> None:
    path = org("/audit-events")
    api.on(
        "GET",
        path,
        Reply(
            json={
                "items": [{**MEMBER_REMOVED, "actor": {"type": "robot"}}],
                "nextCursor": None,
            }
        ),
    )

    [event] = make_client(api).audit_events.list().items

    assert isinstance(event, AuditEventMemberRemoved)
    assert isinstance(event.actor, UnknownAuditEventActor)
    assert event.actor.type == "robot"


# --- Public endpoints, files ----------------------------------------------


def test_public_endpoints_send_no_access_token(api: FakeApi) -> None:
    api.on(
        "GET",
        "/courses",
        Reply(
            json={
                "items": [
                    {
                        "courseId": "hipaa-essentials",
                        "title": "HIPAA Essentials",
                        "courseVersion": "2026.1",
                        "passingThreshold": 0.8,
                    }
                ],
                "nextCursor": None,
            }
        ),
    )

    page = make_client(api).courses.list()

    assert page.items[0].passing_threshold == 0.8
    [request] = api.requests_to("GET", "/courses")
    assert "authorization" not in request.headers
    assert api.requests_to("POST", "/auth/token") == []


def test_a_certificate_pdf_downloads_as_bytes(api: FakeApi) -> None:
    path = org(f"/certificates/{CERTIFICATE_ID}/content")
    pdf = b"%PDF-1.7\n\xe2\xe3\xcf\xd3\n%%EOF\n"
    api.on(
        "GET",
        path,
        Reply(
            content=pdf,
            content_type="application/pdf",
            headers={"content-disposition": 'attachment; filename="certificate.pdf"'},
        ),
    )

    download = make_client(api).certificates.download_pdf(CERTIFICATE_ID)

    assert download.content == pdf
    assert download.content_type == "application/pdf"
    assert download.filename == "certificate.pdf"
    assert download.last_response.status == 200
    [request] = api.requests_to("GET", path)
    assert request.headers["accept"] == "application/pdf, application/problem+json"


def test_previewing_an_import_sends_the_csv_and_pinned_options(
    api: FakeApi,
) -> None:
    path = org("/enrollments:import")
    api.on(
        "POST",
        path,
        Reply(
            json={
                "totalRows": 1,
                "validRows": 1,
                "seatsRequired": 1,
                "seatsAvailable": 4,
                "rows": [
                    {
                        "rowNumber": 2,
                        "email": "ana@example.com",
                        "courseId": "hipaa-essentials",
                        "status": "valid",
                    }
                ],
            }
        ),
    )
    csv = b"email,name\nana@example.com,Ana Lima\n"

    preview = make_client(api).enrollments.preview_import(
        file=csv, options={"course_id": "hipaa-essentials"}
    )

    assert preview.rows[0].status == "valid"
    [request] = api.requests_to("POST", path)
    assert request.headers["content-type"].startswith("multipart/form-data")
    body = request.content
    assert b'name="file"; filename="file.csv"' in body
    assert b"Content-Type: text/csv" in body
    assert csv in body
    assert b'name="options"' in body
    assert b'{"courseId": "hipaa-essentials", "validateOnly": true}' in body
