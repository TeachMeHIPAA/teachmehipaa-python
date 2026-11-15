# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.

from .._core._pipeline import AsyncPipeline, SyncPipeline
from .audit_events import AsyncAuditEvents, AuditEvents
from .auth import AsyncAuth, Auth
from .certificate_verifications import (
    AsyncCertificateVerifications,
    CertificateVerifications,
)
from .certificates import AsyncCertificates, Certificates
from .compliance import AsyncCompliance, Compliance
from .courses import AsyncCourses, Courses
from .enrollments import AsyncEnrollments, Enrollments
from .events import AsyncEvents, Events
from .learners import AsyncLearners, Learners
from .members import AsyncMembers, Members
from .operations import AsyncOperations, Operations
from .partners import AsyncPartners, Partners
from .payment_method import AsyncPaymentMethod, PaymentMethod
from .seat_orders import AsyncSeatOrders, SeatOrders
from .seats import AsyncSeats, Seats
from .webhook_subscriptions import AsyncWebhookSubscriptions, WebhookSubscriptions


class SyncResources:
    """Every top-level resource, attached to a client."""

    audit_events: AuditEvents
    auth: Auth
    certificate_verifications: CertificateVerifications
    certificates: Certificates
    compliance: Compliance
    courses: Courses
    enrollments: Enrollments
    events: Events
    learners: Learners
    members: Members
    operations: Operations
    partners: Partners
    payment_method: PaymentMethod
    seat_orders: SeatOrders
    seats: Seats
    webhook_subscriptions: WebhookSubscriptions

    def __init__(self, pipeline: SyncPipeline) -> None:
        self.audit_events = AuditEvents(pipeline)
        self.auth = Auth(pipeline)
        self.certificate_verifications = CertificateVerifications(pipeline)
        self.certificates = Certificates(pipeline)
        self.compliance = Compliance(pipeline)
        self.courses = Courses(pipeline)
        self.enrollments = Enrollments(pipeline)
        self.events = Events(pipeline)
        self.learners = Learners(pipeline)
        self.members = Members(pipeline)
        self.operations = Operations(pipeline)
        self.partners = Partners(pipeline)
        self.payment_method = PaymentMethod(pipeline)
        self.seat_orders = SeatOrders(pipeline)
        self.seats = Seats(pipeline)
        self.webhook_subscriptions = WebhookSubscriptions(pipeline)


class AsyncResources:
    """Every top-level resource, attached to a client."""

    audit_events: AsyncAuditEvents
    auth: AsyncAuth
    certificate_verifications: AsyncCertificateVerifications
    certificates: AsyncCertificates
    compliance: AsyncCompliance
    courses: AsyncCourses
    enrollments: AsyncEnrollments
    events: AsyncEvents
    learners: AsyncLearners
    members: AsyncMembers
    operations: AsyncOperations
    partners: AsyncPartners
    payment_method: AsyncPaymentMethod
    seat_orders: AsyncSeatOrders
    seats: AsyncSeats
    webhook_subscriptions: AsyncWebhookSubscriptions

    def __init__(self, pipeline: AsyncPipeline) -> None:
        self.audit_events = AsyncAuditEvents(pipeline)
        self.auth = AsyncAuth(pipeline)
        self.certificate_verifications = AsyncCertificateVerifications(pipeline)
        self.certificates = AsyncCertificates(pipeline)
        self.compliance = AsyncCompliance(pipeline)
        self.courses = AsyncCourses(pipeline)
        self.enrollments = AsyncEnrollments(pipeline)
        self.events = AsyncEvents(pipeline)
        self.learners = AsyncLearners(pipeline)
        self.members = AsyncMembers(pipeline)
        self.operations = AsyncOperations(pipeline)
        self.partners = AsyncPartners(pipeline)
        self.payment_method = AsyncPaymentMethod(pipeline)
        self.seat_orders = AsyncSeatOrders(pipeline)
        self.seats = AsyncSeats(pipeline)
        self.webhook_subscriptions = AsyncWebhookSubscriptions(pipeline)
