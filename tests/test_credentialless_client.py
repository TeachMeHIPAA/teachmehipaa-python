"""A client with no credentials can make public lookups, and nothing else."""

from __future__ import annotations

from typing import Any

import pytest

from teachmehipaa import AsyncTeachMeHipaa, TeachMeHipaa
from tests.fake_api import CLIENT_ID, CLIENT_SECRET, SANDBOX_BASE, FakeApi, Reply

TINY_ID = "aB3dE9"

# `dev#/components/schemas/CourseDto`.
COURSE_JSON: dict[str, Any] = {
    "courseId": "hipaa-essentials",
    "title": "HIPAA Essentials",
    "courseVersion": "2026.1",
    "passingThreshold": 0.8,
}

# `dev#/components/schemas/CertificateVerificationDto`.
VERIFICATION_JSON: dict[str, Any] = {
    "status": "valid",
    "learnerName": "Ana Lima",
    "courseTitle": "HIPAA Essentials",
    "issuedAt": "2026-11-02T10:30:00Z",
    "expiresAt": "2027-11-02T10:30:00Z",
    "issuer": "TeachMeHIPAA",
}


def public_api() -> FakeApi:
    api = FakeApi(SANDBOX_BASE)
    api.on("GET", "/courses", Reply(json={"items": [COURSE_JSON], "nextCursor": None}))
    api.on(
        "GET", f"/certificate-verifications/{TINY_ID}", Reply(json=VERIFICATION_JSON)
    )
    return api


def test_lists_courses_and_looks_up_a_certificate_verification() -> None:
    api = public_api()
    client = TeachMeHipaa(environment="sandbox", http_client=api.sync_client())

    page = client.courses.list()
    verification = client.certificate_verifications.retrieve(TINY_ID)

    assert page.items[0].title == "HIPAA Essentials"
    assert verification.status == "valid"
    assert [str(request.url) for request in api.requests] == [
        f"{SANDBOX_BASE}/courses",
        f"{SANDBOX_BASE}/certificate-verifications/{TINY_ID}",
    ]
    assert all("authorization" not in request.headers for request in api.requests)


async def test_async_lists_courses_and_looks_up_a_certificate_verification() -> None:
    api = public_api()
    client = AsyncTeachMeHipaa(environment="sandbox", http_client=api.async_client())

    page = await client.courses.list()
    verification = await client.certificate_verifications.retrieve(TINY_ID)

    assert page.items[0].title == "HIPAA Essentials"
    assert verification.learner_name == "Ana Lima"
    assert len(api.requests) == 2
    assert all("authorization" not in request.headers for request in api.requests)


NO_CREDENTIALS = (
    r"^GET /organizations/\{orgId\}/learners needs credentials, and this client "
    r"has none; pass client_id and client_secret, or a token_provider"
)


def test_refuses_an_organization_scoped_call_before_any_request() -> None:
    api = FakeApi()
    client = TeachMeHipaa(http_client=api.sync_client())

    with pytest.raises(ValueError, match=NO_CREDENTIALS):
        client.learners.list()

    assert api.requests == []


def test_refuses_a_call_that_isnt_organization_scoped_before_any_request() -> None:
    api = FakeApi()
    client = TeachMeHipaa(http_client=api.sync_client())

    with pytest.raises(ValueError, match=r"^GET /auth/introspection needs credentials"):
        client.auth.introspect()

    assert api.requests == []


async def test_async_refuses_an_authenticated_call_before_any_request() -> None:
    api = FakeApi()
    client = AsyncTeachMeHipaa(http_client=api.async_client())

    with pytest.raises(ValueError, match=NO_CREDENTIALS):
        await client.learners.list()

    assert api.requests == []


@pytest.mark.parametrize(
    ("credentials", "client_class"),
    [
        ({"client_id": CLIENT_ID}, TeachMeHipaa),
        ({"client_secret": CLIENT_SECRET}, TeachMeHipaa),
        ({"scopes": ["learners:read"]}, TeachMeHipaa),
        ({"client_id": CLIENT_ID}, AsyncTeachMeHipaa),
        ({"client_secret": CLIENT_SECRET}, AsyncTeachMeHipaa),
    ],
)
def test_still_refuses_half_a_credential_pair(
    credentials: dict[str, Any], client_class: type[TeachMeHipaa | AsyncTeachMeHipaa]
) -> None:
    with pytest.raises(TypeError, match="pass client_id and client_secret"):
        client_class(**credentials)
