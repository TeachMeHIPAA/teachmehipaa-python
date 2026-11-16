"""The public client against a Prism mock of the vendored developer spec: one
representative call per resource family, on both clients. A request that
breaks the spec fails the call (Prism answers 4xx) or the test (a violation
in `sl-violations`)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import httpx
import pytest

from teachmehipaa import (
    AsyncStaticTokenProvider,
    AsyncTeachMeHipaa,
    InvalidRequestError,
    StaticTokenProvider,
    TeachMeHipaa,
)
from tests.contract.conftest import Violations

pytestmark = pytest.mark.contract

# Values that satisfy the spec's path-parameter patterns.
ORG_ID = "org_acme"
LEARNER_ID = "sub_01JD80AB2C3D4E5F6G7H8J9K0M"
ENROLLMENT_ID = "sub_01JD80AB2C3D4E5F6G7H8J9K0M__hipaa-2026"
CERTIFICATE_ID = "cert_01JD8F"
COURSE_ID = "hipaa-2026"
SUBSCRIPTION_ID = "whs_01JD8D"
OPERATION_ID = "op-01JD8H"
TINY_ID = "cAbCdEfGhIjKl"
TOKEN = "contract-test-token"


@pytest.fixture
def sync_client(prism_url: str, violations: Violations) -> Iterator[TeachMeHipaa]:
    # Prism can't mint tokens from the form-encoded `/auth/token`, so the
    # client sends a static one and skips Organization discovery.
    with TeachMeHipaa(
        token_provider=StaticTokenProvider(TOKEN),
        organization_id=ORG_ID,
        base_url=prism_url,
        max_retries=0,
        http_client=httpx.Client(event_hooks={"response": [violations.record]}),
    ) as client:
        yield client


@pytest.fixture
async def async_client(
    prism_url: str, violations: Violations
) -> AsyncIterator[AsyncTeachMeHipaa]:
    async with AsyncTeachMeHipaa(
        token_provider=AsyncStaticTokenProvider(TOKEN),
        organization_id=ORG_ID,
        base_url=prism_url,
        max_retries=0,
        http_client=httpx.AsyncClient(event_hooks={"response": [violations.arecord]}),
    ) as client:
        yield client


async def test_the_harness_catches_a_request_that_breaks_the_spec(
    sync_client: TeachMeHipaa,
    async_client: AsyncTeachMeHipaa,
    violations: Violations,
) -> None:
    with pytest.raises(InvalidRequestError):
        sync_client.learners.list(limit=0)
    with pytest.raises(InvalidRequestError):
        await async_client.learners.list(limit=0)

    assert len(violations.found) == 2
    assert all("limit" in violation for violation in violations.found)
    violations.found.clear()


async def test_lists_courses_as_a_page(
    sync_client: TeachMeHipaa, async_client: AsyncTeachMeHipaa
) -> None:
    pages = (
        sync_client.courses.list(limit=5),
        await async_client.courses.list(limit=5),
    )

    for page in pages:
        for course in page.items:
            assert isinstance(course.course_id, str)
            assert isinstance(course.passing_threshold, (int, float))
        assert page.last_response.status == 200


async def test_retrieves_a_course(
    sync_client: TeachMeHipaa, async_client: AsyncTeachMeHipaa
) -> None:
    for course in (
        sync_client.courses.retrieve(COURSE_ID),
        await async_client.courses.retrieve(COURSE_ID),
    ):
        assert isinstance(course.title, str)


async def test_retrieves_a_certificate_verification(
    sync_client: TeachMeHipaa, async_client: AsyncTeachMeHipaa
) -> None:
    for verification in (
        sync_client.certificate_verifications.retrieve(TINY_ID),
        await async_client.certificate_verifications.retrieve(TINY_ID),
    ):
        assert isinstance(verification.learner_name, str)
        assert isinstance(verification.issuer, str)


async def test_creates_a_learner_and_reports_whether_it_was_created(
    sync_client: TeachMeHipaa, async_client: AsyncTeachMeHipaa
) -> None:
    for result in (
        sync_client.learners.create(
            email="ana@example.com",
            name="Ana Example",
            external_id="hr-123",
            course_id=COURSE_ID,
            delivery="none",
        ),
        await async_client.learners.create(
            email="ana@example.com",
            name="Ana Example",
            external_id="hr-123",
            course_id=COURSE_ID,
            delivery="none",
        ),
    ):
        assert isinstance(result.learner_id, str)
        assert isinstance(result.created, bool)


async def test_lists_learners_with_filters(
    sync_client: TeachMeHipaa, async_client: AsyncTeachMeHipaa
) -> None:
    pages = (
        sync_client.learners.list(
            limit=10, status="in_progress", email="ana@example.com"
        ),
        await async_client.learners.list(
            limit=10, status="in_progress", email="ana@example.com"
        ),
    )

    for page in pages:
        for learner in page.items:
            assert isinstance(learner.email, str)


async def test_retrieves_a_learner(
    sync_client: TeachMeHipaa, async_client: AsyncTeachMeHipaa
) -> None:
    for learner in (
        sync_client.learners.retrieve(LEARNER_ID, course_id=COURSE_ID),
        await async_client.learners.retrieve(LEARNER_ID, course_id=COURSE_ID),
    ):
        assert isinstance(learner.learner_id, str)
        assert isinstance(learner.course.course_id, str)


async def test_updates_a_learner_as_a_merge_patch_with_if_match(
    sync_client: TeachMeHipaa, async_client: AsyncTeachMeHipaa
) -> None:
    for learner in (
        sync_client.learners.update(
            LEARNER_ID, if_match='"7"', name="Ana Q. Example", external_id=None
        ),
        await async_client.learners.update(
            LEARNER_ID, if_match='"7"', name="Ana Q. Example", external_id=None
        ),
    ):
        assert isinstance(learner.learner_id, str)


async def test_cancels_an_enrollment(
    sync_client: TeachMeHipaa, async_client: AsyncTeachMeHipaa
) -> None:
    for result in (
        sync_client.enrollments.cancel(ENROLLMENT_ID, refund=False),
        await async_client.enrollments.cancel(ENROLLMENT_ID, refund=False),
    ):
        assert result.last_response.status == 200


async def test_retrieves_a_certificate(
    sync_client: TeachMeHipaa, async_client: AsyncTeachMeHipaa
) -> None:
    for certificate in (
        sync_client.certificates.retrieve(CERTIFICATE_ID),
        await async_client.certificates.retrieve(CERTIFICATE_ID),
    ):
        assert isinstance(certificate.certificate_id, str)


async def test_downloads_a_certificate_pdf(
    sync_client: TeachMeHipaa, async_client: AsyncTeachMeHipaa
) -> None:
    for pdf in (
        sync_client.certificates.download_pdf(CERTIFICATE_ID),
        await async_client.certificates.download_pdf(CERTIFICATE_ID),
    ):
        assert isinstance(pdf.content, bytes)
        assert (pdf.content_type or "").startswith("application/pdf")


async def test_creates_a_webhook_subscription_with_its_signing_secret(
    sync_client: TeachMeHipaa, async_client: AsyncTeachMeHipaa
) -> None:
    for subscription in (
        sync_client.webhook_subscriptions.create(
            endpoint_url="https://hr.example.com/hooks/tmh",
            event_types=["learner.certified", "seats.low"],
            description="HR sync",
            seats_low_threshold=5,
        ),
        await async_client.webhook_subscriptions.create(
            endpoint_url="https://hr.example.com/hooks/tmh",
            event_types=["learner.certified", "seats.low"],
            description="HR sync",
            seats_low_threshold=5,
        ),
    ):
        assert isinstance(subscription.subscription_id, str)
        assert isinstance(subscription.secret, str)


async def test_deletes_a_webhook_subscription(
    sync_client: TeachMeHipaa, async_client: AsyncTeachMeHipaa
) -> None:
    # Both return None for the 204; reaching the end without an error is
    # the assertion.
    sync_client.webhook_subscriptions.delete(SUBSCRIPTION_ID)
    await async_client.webhook_subscriptions.delete(SUBSCRIPTION_ID)


async def test_lists_the_event_log(
    sync_client: TeachMeHipaa, async_client: AsyncTeachMeHipaa
) -> None:
    pages = (
        sync_client.events.list(limit=25),
        await async_client.events.list(limit=25),
    )

    for page in pages:
        for event in page.items:
            assert isinstance(event.event_type, str)


async def test_retrieves_an_operation(
    sync_client: TeachMeHipaa, async_client: AsyncTeachMeHipaa
) -> None:
    sync_operation = sync_client.operations.retrieve(OPERATION_ID)
    async_operation = await async_client.operations.retrieve(OPERATION_ID)

    assert isinstance(sync_operation.name, str)
    assert isinstance(async_operation.name, str)
    assert callable(sync_operation.wait)
    assert callable(async_operation.wait)


async def test_introspects_the_access_token(
    sync_client: TeachMeHipaa, async_client: AsyncTeachMeHipaa
) -> None:
    for introspection in (
        sync_client.auth.introspect(),
        await async_client.auth.introspect(),
    ):
        assert isinstance(introspection.actor_type, str)
