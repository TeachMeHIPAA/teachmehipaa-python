# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.

from datetime import datetime
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import Discriminator, Field, Tag

from .._core._models import BaseModel
from .._core._pagination import PageBody
from .._core._unions import UNKNOWN_VARIANT, by_presence, by_property

AccessTokenResponseScopesItem: TypeAlias = (
    Literal[
        "me",
        "enrollments:read",
        "enrollments:write",
        "members:read",
        "members:admin",
        "certificates:read",
        "certificates:write",
        "billing:write",
        "org:admin",
        "audit:read",
        "scim",
        "support:write",
        "learners:read",
        "learners:write",
        "compliance:read",
        "seats:purchase",
        "webhooks:manage",
        "partner:orgs:read",
        "partner:orgs:write",
    ]
    | str
)


AccessTokenResponseTokenType: TypeAlias = Literal["Bearer"] | str


class AccessTokenResponse(BaseModel):
    token_type: AccessTokenResponseTokenType
    access_token: str
    expires_in_sec: int
    scopes: list[AccessTokenResponseScopesItem]


class AuditEventActorAgent(BaseModel):
    type: Literal["agent"]
    agent_id: str


class AuditEventActorClient(BaseModel):
    type: Literal["client"]
    client_id: str


class AuditEventActorScim(BaseModel):
    type: Literal["scim"]
    key_id: str


class AuditEventActorUser(BaseModel):
    type: Literal["user"]
    subject_id: str


class UnknownAuditEventActor(BaseModel):
    """A `AuditEventActor` of a kind this version of the library doesn't know. Its other
    fields are kept in `model_extra`.
    """

    type: str


AuditEventActor: TypeAlias = Annotated[
    Annotated[AuditEventActorAgent, Tag("agent")]
    | Annotated[AuditEventActorClient, Tag("client")]
    | Annotated[AuditEventActorScim, Tag("scim")]
    | Annotated[AuditEventActorUser, Tag("user")]
    | Annotated[UnknownAuditEventActor, Tag(UNKNOWN_VARIANT)],
    Discriminator(
        by_property("type", "type", frozenset({"agent", "client", "scim", "user"}))
    ),
]


class AuditEventApiClientCreated(BaseModel):
    event_id: str
    at: str
    type: Literal["api_client.created"]
    actor_subject_id: str
    actor: AuditEventActor
    client_id: str


class AuditEventApiClientRevoked(BaseModel):
    event_id: str
    at: str
    type: Literal["api_client.revoked"]
    actor_subject_id: str
    actor: AuditEventActor
    client_id: str


class AuditEventApiClientSecretRotated(BaseModel):
    event_id: str
    at: str
    type: Literal["api_client.secret_rotated"]
    actor_subject_id: str
    actor: AuditEventActor
    client_id: str


AuditEventApiClientUpdatedFieldsItem: TypeAlias = (
    Literal["name", "maxSeatsPerOrder", "maxSpendPer30Days", "returnUrlAllowlist"] | str
)


class AuditEventApiClientUpdated(BaseModel):
    event_id: str
    at: str
    type: Literal["api_client.updated"]
    actor_subject_id: str
    actor: AuditEventActor
    client_id: str
    fields: list[AuditEventApiClientUpdatedFieldsItem]


class AuditEventCertificateIssued(BaseModel):
    event_id: str
    at: str
    type: Literal["certificate.issued"]
    actor_subject_id: str
    actor: AuditEventActor
    certificate_id: str
    subject_id: str | None
    course_id: str


class AuditEventCertificateRevoked(BaseModel):
    event_id: str
    at: str
    type: Literal["certificate.revoked"]
    actor_subject_id: str
    actor: AuditEventActor
    certificate_id: str
    subject_id: str | None
    course_id: str


AuditEventEnrollmentTransitionStatusFrom: TypeAlias = (
    Literal[
        "INVITED",
        "EMAIL_BOUNCED",
        "STARTED",
        "ASSESSMENT_IN_PROGRESS",
        "CERTIFIED",
        "CANCELLED",
    ]
    | str
)


AuditEventEnrollmentTransitionStatusTo: TypeAlias = (
    Literal[
        "INVITED",
        "EMAIL_BOUNCED",
        "STARTED",
        "ASSESSMENT_IN_PROGRESS",
        "CERTIFIED",
        "CANCELLED",
    ]
    | str
)


AuditEventEnrollmentTransitionTransition: TypeAlias = (
    Literal[
        "bounce",
        "start",
        "beginAssessment",
        "submitAssessment",
        "certify",
        "revokeCert",
        "archive",
        "unarchive",
        "reinvite",
        "cancelInvite",
    ]
    | str
)


class AuditEventEnrollmentTransition(BaseModel):
    event_id: str
    at: str
    type: Literal["enrollment.transition"]
    transition: AuditEventEnrollmentTransitionTransition
    subject_id: str
    course_id: str
    status_from: AuditEventEnrollmentTransitionStatusFrom
    status_to: AuditEventEnrollmentTransitionStatusTo
    archived_from: bool
    archived_to: bool
    rev: int


class AuditEventLearnerLaunchLinkCreated(BaseModel):
    event_id: str
    at: str
    type: Literal["learner.launch_link_created"]
    actor_subject_id: str
    actor: AuditEventActor
    subject_id: str
    course_id: str


AuditEventLearnerUpdatedFieldsItem: TypeAlias = Literal["name", "externalId"] | str


class AuditEventLearnerUpdated(BaseModel):
    event_id: str
    at: str
    type: Literal["learner.updated"]
    actor_subject_id: str
    actor: AuditEventActor
    subject_id: str
    fields: list[AuditEventLearnerUpdatedFieldsItem]


class AuditEventMemberRemoved(BaseModel):
    event_id: str
    at: str
    type: Literal["member.removed"]
    actor_subject_id: str
    actor: AuditEventActor
    subject_id: str
    was_admin: bool


AuditEventMemberRoleChangedRoleFrom: TypeAlias = Literal["admin", "learner"] | str


AuditEventMemberRoleChangedRoleTo: TypeAlias = Literal["admin", "learner"] | str


class AuditEventMemberRoleChanged(BaseModel):
    event_id: str
    at: str
    type: Literal["member.role_changed"]
    actor_subject_id: str
    actor: AuditEventActor
    subject_id: str
    role_from: AuditEventMemberRoleChangedRoleFrom
    role_to: AuditEventMemberRoleChangedRoleTo


class AuditEventMemberTransferred(BaseModel):
    event_id: str
    at: str
    type: Literal["member.transferred"]
    actor_subject_id: str
    actor: AuditEventActor
    subject_id: str
    target_org_id: str


AuditEventOauthGrantCreatedScopesItem: TypeAlias = (
    Literal[
        "enrollments:read",
        "enrollments:write",
        "certificates:read",
        "members:read",
        "audit:read",
        "learners:read",
        "learners:write",
        "compliance:read",
        "seats:purchase",
        "webhooks:manage",
    ]
    | str
)


class AuditEventOauthGrantCreated(BaseModel):
    event_id: str
    at: str
    type: Literal["oauth_grant.created"]
    actor_subject_id: str
    actor: AuditEventActor
    app_id: str
    grant_id: str
    scopes: list[AuditEventOauthGrantCreatedScopesItem]


AuditEventOauthGrantRevokedReason: TypeAlias = (
    Literal["admin", "code_reuse", "refresh_token_reuse"] | str
)


class AuditEventOauthGrantRevoked(BaseModel):
    event_id: str
    at: str
    type: Literal["oauth_grant.revoked"]
    actor_subject_id: str
    actor: AuditEventActor
    app_id: str
    grant_id: str
    reason: AuditEventOauthGrantRevokedReason


AuditEventOauthGrantUpdatedFieldsItem: TypeAlias = (
    Literal["maxSeatsPerOrder", "maxSpendPer30Days"] | str
)


class AuditEventOauthGrantUpdated(BaseModel):
    event_id: str
    at: str
    type: Literal["oauth_grant.updated"]
    actor_subject_id: str
    actor: AuditEventActor
    app_id: str
    grant_id: str
    fields: list[AuditEventOauthGrantUpdatedFieldsItem]


class AuditEventOrganizationClosed(BaseModel):
    event_id: str
    at: str
    type: Literal["organization.closed"]
    actor_subject_id: str
    actor: AuditEventActor


class AuditEventOrganizationCreatedByPartner(BaseModel):
    event_id: str
    at: str
    type: Literal["organization.created_by_partner"]
    actor_subject_id: str
    actor: AuditEventActor
    partner_id: str
    app_id: str
    grant_id: str


class AuditEventOrganizationReopened(BaseModel):
    event_id: str
    at: str
    type: Literal["organization.reopened"]
    actor_subject_id: str
    actor: AuditEventActor


AuditEventOrganizationUpdatedFieldsItem: TypeAlias = (
    Literal["name", "trainingNeeds", "snoozeDuration", "autoRecertify"] | str
)


class AuditEventOrganizationUpdated(BaseModel):
    event_id: str
    at: str
    type: Literal["organization.updated"]
    actor_subject_id: str
    actor: AuditEventActor
    fields: list[AuditEventOrganizationUpdatedFieldsItem]


class AuditEventSeatGranted(BaseModel):
    event_id: str
    at: str
    type: Literal["seat.granted"]
    actor_subject_id: str
    actor: AuditEventActor
    quantity: int


AuditEventPaymentMethod: TypeAlias = (
    Literal["hosted_checkout", "saved_payment_method", "invoice"] | str
)


class AuditEventSeatOrderCreated(BaseModel):
    event_id: str
    at: str
    actor_subject_id: str
    actor: AuditEventActor
    seat_order_id: str
    quantity: int
    payment_method: AuditEventPaymentMethod
    type: Literal["seat_order.created"]
    grant_id: str | None = None


class AuditEventSeatOrderFailed(BaseModel):
    event_id: str
    at: str
    actor_subject_id: str
    actor: AuditEventActor
    seat_order_id: str
    quantity: int
    payment_method: AuditEventPaymentMethod
    type: Literal["seat_order.failed"]
    failure_code: str | None


class AuditEventSeatOrderPaid(BaseModel):
    event_id: str
    at: str
    actor_subject_id: str
    actor: AuditEventActor
    seat_order_id: str
    quantity: int
    payment_method: AuditEventPaymentMethod
    type: Literal["seat_order.paid"]


class UnknownAuditEvent(BaseModel):
    """A `AuditEvent` of a kind this version of the library doesn't know. Its other
    fields are kept in `model_extra`.
    """

    type: str


AuditEvent: TypeAlias = Annotated[
    Annotated[AuditEventApiClientCreated, Tag("api_client.created")]
    | Annotated[AuditEventApiClientRevoked, Tag("api_client.revoked")]
    | Annotated[AuditEventApiClientSecretRotated, Tag("api_client.secret_rotated")]
    | Annotated[AuditEventApiClientUpdated, Tag("api_client.updated")]
    | Annotated[AuditEventCertificateIssued, Tag("certificate.issued")]
    | Annotated[AuditEventCertificateRevoked, Tag("certificate.revoked")]
    | Annotated[AuditEventEnrollmentTransition, Tag("enrollment.transition")]
    | Annotated[AuditEventLearnerLaunchLinkCreated, Tag("learner.launch_link_created")]
    | Annotated[AuditEventLearnerUpdated, Tag("learner.updated")]
    | Annotated[AuditEventMemberRemoved, Tag("member.removed")]
    | Annotated[AuditEventMemberRoleChanged, Tag("member.role_changed")]
    | Annotated[AuditEventMemberTransferred, Tag("member.transferred")]
    | Annotated[AuditEventOauthGrantCreated, Tag("oauth_grant.created")]
    | Annotated[AuditEventOauthGrantRevoked, Tag("oauth_grant.revoked")]
    | Annotated[AuditEventOauthGrantUpdated, Tag("oauth_grant.updated")]
    | Annotated[AuditEventOrganizationClosed, Tag("organization.closed")]
    | Annotated[
        AuditEventOrganizationCreatedByPartner, Tag("organization.created_by_partner")
    ]
    | Annotated[AuditEventOrganizationReopened, Tag("organization.reopened")]
    | Annotated[AuditEventOrganizationUpdated, Tag("organization.updated")]
    | Annotated[AuditEventSeatGranted, Tag("seat.granted")]
    | Annotated[AuditEventSeatOrderCreated, Tag("seat_order.created")]
    | Annotated[AuditEventSeatOrderFailed, Tag("seat_order.failed")]
    | Annotated[AuditEventSeatOrderPaid, Tag("seat_order.paid")]
    | Annotated[UnknownAuditEvent, Tag(UNKNOWN_VARIANT)],
    Discriminator(
        by_property(
            "type",
            "type",
            frozenset(
                {
                    "api_client.created",
                    "api_client.revoked",
                    "api_client.secret_rotated",
                    "api_client.updated",
                    "certificate.issued",
                    "certificate.revoked",
                    "enrollment.transition",
                    "learner.launch_link_created",
                    "learner.updated",
                    "member.removed",
                    "member.role_changed",
                    "member.transferred",
                    "oauth_grant.created",
                    "oauth_grant.revoked",
                    "oauth_grant.updated",
                    "organization.closed",
                    "organization.created_by_partner",
                    "organization.reopened",
                    "organization.updated",
                    "seat.granted",
                    "seat_order.created",
                    "seat_order.failed",
                    "seat_order.paid",
                }
            ),
        )
    ),
]


class AuditEventsPage(PageBody[AuditEvent]):
    pass


AuthorizationCodeTokenResponseTokenType: TypeAlias = Literal["Bearer"] | str


class AuthorizationCodeTokenResponse(BaseModel):
    access_token: str = Field(alias="access_token")
    token_type: AuthorizationCodeTokenResponseTokenType = Field(alias="token_type")
    expires_in: int = Field(alias="expires_in")
    refresh_token: str = Field(alias="refresh_token")
    scope: str


class PaymentMethodSavedByApiClient(BaseModel):
    type: Literal["api_client"]
    name: str


class PaymentMethodSavedByUser(BaseModel):
    type: Literal["user"]
    name: str


class UnknownPaymentMethodSavedBy(BaseModel):
    """A `PaymentMethodSavedBy` of a kind this version of the library doesn't know. Its
    other fields are kept in `model_extra`.
    """

    type: str


PaymentMethodSavedBy: TypeAlias = Annotated[
    Annotated[PaymentMethodSavedByApiClient, Tag("api_client")]
    | Annotated[PaymentMethodSavedByUser, Tag("user")]
    | Annotated[UnknownPaymentMethodSavedBy, Tag(UNKNOWN_VARIANT)],
    Discriminator(by_property("type", "type", frozenset({"api_client", "user"}))),
]


class BillingPaymentMethodDefaultPaymentMethod(BaseModel):
    brand: str
    last4: str
    exp_month: int
    exp_year: int
    payment_method_id: str | None
    saved_by: PaymentMethodSavedBy | None
    saved_at: datetime | None
    expired: bool


class BillingPaymentMethod(BaseModel):
    default_payment_method: BillingPaymentMethodDefaultPaymentMethod | None
    """The saved card's brand, last four digits, expiry and id, or `null` when none is
    saved.
    """
    chargeable: bool
    """Whether a `saved_payment_method` order would charge it now."""


EnrollmentEffectiveStatus: TypeAlias = (
    Literal[
        "INVITED",
        "EMAIL_BOUNCED",
        "STARTED",
        "ASSESSMENT_IN_PROGRESS",
        "CERTIFIED",
        "CANCELLED",
        "EXPIRING",
        "EXPIRED",
        "ARCHIVED",
    ]
    | str
)
"""The status to display. Adds `EXPIRING`, `EXPIRED` and `ARCHIVED`, derived when you
read it.
"""


EnrollmentStatus: TypeAlias = (
    Literal[
        "INVITED",
        "EMAIL_BOUNCED",
        "STARTED",
        "ASSESSMENT_IN_PROGRESS",
        "CERTIFIED",
        "CANCELLED",
    ]
    | str
)
"""The stored lifecycle state: `INVITED`, `EMAIL_BOUNCED`, `STARTED`,
`ASSESSMENT_IN_PROGRESS`, `CERTIFIED` or `CANCELLED`.
"""


class Enrollment(BaseModel):
    enrollment_id: str
    """Unique identifier for the enrollment."""
    subject_id: str
    """The learner's member id."""
    course_id: str
    """The course."""
    org_id: str
    """The organization's id."""
    status: EnrollmentStatus
    """The stored lifecycle state: `INVITED`, `EMAIL_BOUNCED`, `STARTED`,
    `ASSESSMENT_IN_PROGRESS`, `CERTIFIED` or `CANCELLED`.
    """
    effective_status: EnrollmentEffectiveStatus
    """The status to display. Adds `EXPIRING`, `EXPIRED` and `ARCHIVED`, derived when
    you read it.
    """
    archived: bool
    """Whether the enrollment is archived."""
    cycle: int
    """The certification cycle, starting at 0. Renewing adds one."""
    rev: int
    """The resource's revision. Its strong `ETag` is derived from it."""
    invited_at: str | None
    """When the learner was invited (ISO 8601)."""
    started_at: str | None
    """When the learner started."""
    completed_at: str | None
    """When the learner completed the course."""
    certified_at: str | None
    """When the learner was certified."""
    expires_at: str | None
    """When the certification expires."""
    certificate_id: str | None
    """The certificate issued for this cycle, if any."""


EnrollmentCancelRefundedEffectiveStatus: TypeAlias = (
    Literal[
        "INVITED",
        "EMAIL_BOUNCED",
        "STARTED",
        "ASSESSMENT_IN_PROGRESS",
        "CERTIFIED",
        "CANCELLED",
        "EXPIRING",
        "EXPIRED",
        "ARCHIVED",
    ]
    | str
)


class EnrollmentCancelRefundedRefund(BaseModel):
    refund_id: str
    amount_cents: int
    currency: str


EnrollmentCancelRefundedStatus: TypeAlias = (
    Literal[
        "INVITED",
        "EMAIL_BOUNCED",
        "STARTED",
        "ASSESSMENT_IN_PROGRESS",
        "CERTIFIED",
        "CANCELLED",
    ]
    | str
)


class EnrollmentCancelRefunded(BaseModel):
    enrollment_id: str
    subject_id: str
    course_id: str
    org_id: str
    status: EnrollmentCancelRefundedStatus
    effective_status: EnrollmentCancelRefundedEffectiveStatus
    archived: bool
    cycle: int
    rev: int
    invited_at: str | None
    started_at: str | None
    completed_at: str | None
    certified_at: str | None
    expires_at: str | None
    certificate_id: str | None
    refund: EnrollmentCancelRefundedRefund


CancelEnrollmentResponse: TypeAlias = Annotated[
    Annotated[EnrollmentCancelRefunded, Tag("EnrollmentCancelRefunded")]
    | Annotated[Enrollment, Tag("Enrollment")],
    Discriminator(by_presence((("refund", "EnrollmentCancelRefunded"),), "Enrollment")),
]


CertificateHolderStatus: TypeAlias = Literal["resolved", "none", "lookup_failed"] | str
"""Whether the holder could be resolved: `resolved`, `none` or `lookup_failed`."""


CertificateStatus: TypeAlias = Literal["VALID", "EXPIRED", "REVOKED"] | str
"""`VALID`, `EXPIRED` or `REVOKED`."""


class Certificate(BaseModel):
    certificate_id: str
    """Unique identifier for the certificate."""
    subject_id: str | None
    """The holder's member id."""
    holder_status: CertificateHolderStatus | None = None
    """Whether the holder could be resolved: `resolved`, `none` or `lookup_failed`."""
    course_id: str
    """The course the certificate is for."""
    course_version: str | None
    """The course version the holder passed."""
    issued_at: str | None
    """When it was issued (ISO 8601)."""
    expires_at: str | None
    """When it expires."""
    status: CertificateStatus
    """`VALID`, `EXPIRED` or `REVOKED`."""
    revoked_at: str | None
    """When it was revoked, if it was."""


class CertificateLinks(BaseModel):
    certificate_id: str
    """The certificate."""
    linked_in_url: str
    """Adds the certificate to the holder's LinkedIn profile."""
    short_link: str
    """The public `tme.so` verification link."""
    tiny_id: str
    """The verification link's id."""
    paywalled: bool | None = None


class CertificateRevokedEventData(BaseModel):
    certificate_id: str
    learner_id: str
    course_id: str


CertificateVerificationIssuer: TypeAlias = Literal["TeachMeHIPAA"] | str
"""Who issued it."""


CertificateVerificationStatus: TypeAlias = Literal["valid", "expired", "revoked"] | str
"""`valid`, `expired` or `revoked`."""


class CertificateVerification(BaseModel):
    status: CertificateVerificationStatus
    """`valid`, `expired` or `revoked`."""
    learner_name: str
    """The name printed on the certificate."""
    course_title: str
    """The course."""
    issued_at: datetime
    """When it was issued (ISO 8601)."""
    expires_at: datetime
    """When it expires."""
    issuer: CertificateVerificationIssuer
    """Who issued it."""


CertificatesExportRequestFormat: TypeAlias = Literal["csv", "zip"] | str
"""The file format. Only `csv` today."""


class CertificatesExportRequest(BaseModel):
    format: CertificatesExportRequestFormat
    """The file format. Only `csv` today."""


class CertificatesPage(PageBody[Certificate]):
    pass


ClientCredentialsTokenResponseTokenType: TypeAlias = Literal["Bearer"] | str
"""Always `Bearer`."""


class ClientCredentialsTokenResponse(BaseModel):
    access_token: str = Field(alias="access_token")
    """The access token. Send it as `Authorization: Bearer`."""
    token_type: ClientCredentialsTokenResponseTokenType = Field(alias="token_type")
    """Always `Bearer`."""
    expires_in: int = Field(alias="expires_in")
    """Seconds until the token expires."""
    scope: str
    """The scopes the token holds, space-delimited."""


class ComplianceSummaryTotals(BaseModel):
    """Learners by status: `learners`, `compliant`, `expiringSoon`, `expired`,
    `inProgress`, `notStarted` and `inviteBounced`.
    """

    learners: int
    compliant: int
    expiring_soon: int
    expired: int
    in_progress: int
    not_started: int
    invite_bounced: int


class ComplianceSummary(BaseModel):
    as_of: datetime
    """When the counts were taken (ISO 8601)."""
    course_id: str
    """The course."""
    totals: ComplianceSummaryTotals
    """Learners by status: `learners`, `compliant`, `expiringSoon`, `expired`,
    `inProgress`, `notStarted` and `inviteBounced`.
    """
    compliant_rate: float
    """`compliant` divided by `learners`, or 0 with no learners."""


class Course(BaseModel):
    course_id: str
    """Unique identifier for the course."""
    title: str
    """The course's title."""
    course_version: str
    """The current version of the course content."""
    passing_threshold: float
    """The score needed to pass the course's assessment."""


class CoursesPage(PageBody[Course]):
    pass


EnrollmentActionAcceptedAction: TypeAlias = Literal["remind", "resendInvite"] | str
"""The action that was accepted: `remind` or `resendInvite`."""


class EnrollmentActionAccepted(BaseModel):
    enrollment_id: str
    """The enrollment the request is for."""
    action: EnrollmentActionAcceptedAction
    """The action that was accepted: `remind` or `resendInvite`."""


class EnrollmentCancelRequest(BaseModel):
    refund: bool | None = None
    """Refund the seat to the card that paid for it instead of returning it to the pool.
    Defaults to `false`.
    """


class EnrollmentCertifiedEventData(BaseModel):
    subject_id: str
    course_id: str
    enrollment_id: str | None = None


class EnrollmentCreateRequest(BaseModel):
    email: str
    """The learner's email address."""
    name: str | None = None
    """The learner's full name."""
    course_id: str | None = None
    """The course to invite them to. Defaults to `hipaa`."""


EnrollmentsBatchRequestOperation: TypeAlias = (
    Literal["remind", "resendInvite", "cancel", "recertify", "archive", "unarchive"]
    | str
)
"""What to do to each enrollment: `remind`, `resendInvite`, `cancel`, `recertify`,
`archive` or `unarchive`.
"""


class EnrollmentsBatchRequestSelectEnrollmentIds(BaseModel):
    enrollment_ids: list[str]


EnrollmentsBatchRequestSelectFilterFilterStatus: TypeAlias = (
    Literal[
        "INVITED",
        "EMAIL_BOUNCED",
        "STARTED",
        "ASSESSMENT_IN_PROGRESS",
        "CERTIFIED",
        "CANCELLED",
        "EXPIRING",
        "EXPIRED",
        "ARCHIVED",
    ]
    | str
)


class EnrollmentsBatchRequestSelectFilterFilter(BaseModel):
    status: EnrollmentsBatchRequestSelectFilterFilterStatus | None = None
    course_id: str | None = None
    archived: bool | None = None


class EnrollmentsBatchRequestSelectFilter(BaseModel):
    filter: EnrollmentsBatchRequestSelectFilterFilter


EnrollmentsBatchRequestSelect: TypeAlias = Annotated[
    Annotated[
        EnrollmentsBatchRequestSelectEnrollmentIds,
        Tag("EnrollmentsBatchRequestSelectEnrollmentIds"),
    ]
    | Annotated[
        EnrollmentsBatchRequestSelectFilter, Tag("EnrollmentsBatchRequestSelectFilter")
    ],
    Discriminator(
        by_presence(
            (
                ("enrollmentIds", "EnrollmentsBatchRequestSelectEnrollmentIds"),
                ("filter", "EnrollmentsBatchRequestSelectFilter"),
            ),
            None,
        )
    ),
]
"""The enrollments to act on: a list of `enrollmentIds` (up to 500), or a `filter`."""


class EnrollmentsBatchRequest(BaseModel):
    operation: EnrollmentsBatchRequestOperation
    """What to do to each enrollment: `remind`, `resendInvite`, `cancel`, `recertify`,
    `archive` or `unarchive`.
    """
    select: EnrollmentsBatchRequestSelect
    """The enrollments to act on: a list of `enrollmentIds` (up to 500), or a `filter`.
    """


EnrollmentsBatchResultsOperation: TypeAlias = (
    Literal["remind", "resendInvite", "cancel", "recertify", "archive", "unarchive"]
    | str
)
"""The operation that was run."""


EnrollmentsBatchResultsResultsItemOutcome: TypeAlias = (
    Literal["succeeded", "skipped", "failed"] | str
)


ProblemCode: TypeAlias = (
    Literal[
        "validation_failed",
        "unauthorized",
        "forbidden",
        "not_found",
        "method_not_allowed",
        "not_acceptable",
        "conflict",
        "rate_limited",
        "precondition_required",
        "precondition_failed",
        "idempotency_key_reuse",
        "unsupported_media_type",
        "illegal_transition",
        "seat_unavailable",
        "seat_already_claimed",
        "already_invited",
        "email_already_registered",
        "last_admin_removal_blocked",
        "org_not_active",
        "enrollment_archived",
        "lessons_incomplete",
        "batch_too_large",
        "import_too_large",
        "export_too_large",
        "summary_too_large",
        "seat_not_refundable",
        "refund_failed",
        "not_configured",
        "reset_unavailable",
        "auto_recertify_unavailable",
        "api_client_limit_reached",
        "external_id_conflict",
        "cannot_offboard_admin",
        "spend_limit_exceeded",
        "payment_method_not_available",
        "return_url_not_allowed",
        "currency_not_available",
        "payment_method_required",
        "payment_method_changed",
        "price_changed",
        "superseded",
        "setup_not_succeeded",
        "invoice_billing_not_enabled",
        "cannot_launch_admin",
        "learner_removed",
        "learner_not_accepted",
        "partner_org_limit_reached",
        "billing_contact_required",
        "cannot_rename_admin",
        "learner_in_multiple_orgs",
        "account_exists_use_sign_in",
        "name_change_not_allowed",
        "temporarily_unavailable",
    ]
    | str
)
"""A machine-readable error code, such as `seat_unavailable`."""


class ProblemErrorsItem(BaseModel):
    path: str
    message: str


class Problem(BaseModel):
    type: str | None = None
    """A URI identifying the problem type."""
    title: str
    """A short summary of the problem."""
    status: int
    """The HTTP status code."""
    detail: str | None = None
    """An explanation of this occurrence."""
    instance: str | None = None
    """Identifies this occurrence."""
    code: ProblemCode
    """A machine-readable error code, such as `seat_unavailable`."""
    errors: list[ProblemErrorsItem] | None = None
    """Each invalid field, with its `path` and `message`."""


class EnrollmentsBatchResultsResultsItem(BaseModel):
    enrollment_id: str
    outcome: EnrollmentsBatchResultsResultsItemOutcome
    problem: Problem | None = None


class EnrollmentsBatchResults(BaseModel):
    operation: EnrollmentsBatchResultsOperation
    """The operation that was run."""
    results: list[EnrollmentsBatchResultsResultsItem]
    """One result per enrollment: `succeeded`, `skipped` or `failed` with a problem."""


EnrollmentsExportRequestFormat: TypeAlias = Literal["csv", "xlsx"] | str
"""The file format. Only `csv` today."""


class EnrollmentsExportRequest(BaseModel):
    format: EnrollmentsExportRequestFormat
    """The file format. Only `csv` today."""


OrgEnrollmentListItemEffectiveStatus: TypeAlias = (
    Literal[
        "INVITED",
        "EMAIL_BOUNCED",
        "STARTED",
        "ASSESSMENT_IN_PROGRESS",
        "CERTIFIED",
        "CANCELLED",
        "EXPIRING",
        "EXPIRED",
        "ARCHIVED",
    ]
    | str
)


OrgEnrollmentListItemPriorCertificateStatus: TypeAlias = (
    Literal["VALID", "EXPIRED"] | str
)


class OrgEnrollmentListItemPriorCertificate(BaseModel):
    certificate_id: str
    issued_at: str | None
    expires_at: str | None
    status: OrgEnrollmentListItemPriorCertificateStatus


OrgEnrollmentListItemStatus: TypeAlias = (
    Literal[
        "INVITED",
        "EMAIL_BOUNCED",
        "STARTED",
        "ASSESSMENT_IN_PROGRESS",
        "CERTIFIED",
        "CANCELLED",
    ]
    | str
)


class OrgEnrollmentListItem(BaseModel):
    enrollment_id: str
    subject_id: str
    course_id: str
    org_id: str
    status: OrgEnrollmentListItemStatus
    effective_status: OrgEnrollmentListItemEffectiveStatus
    archived: bool
    cycle: int
    rev: int
    invited_at: str | None
    started_at: str | None
    completed_at: str | None
    certified_at: str | None
    expires_at: str | None
    certificate_id: str | None
    prior_certificate: OrgEnrollmentListItemPriorCertificate | None = None


class EnrollmentsListPage(PageBody[OrgEnrollmentListItem]):
    pass


class EventCertificateRevoked(BaseModel):
    event_id: str
    event_type: Literal["certificate.revoked"]
    org_id: str
    occurred_at: datetime
    data: CertificateRevokedEventData


class EventEnrollmentCertified(BaseModel):
    event_id: str
    event_type: Literal["enrollment.certified"]
    org_id: str
    occurred_at: datetime
    data: EnrollmentCertifiedEventData


LearnerStatus: TypeAlias = (
    Literal[
        "not_started",
        "invite_bounced",
        "in_progress",
        "compliant",
        "expiring_soon",
        "expired",
        "removed",
    ]
    | str
)


class LearnerEventData(BaseModel):
    learner_id: str
    email: str
    external_id: str | None
    course_id: str
    status: LearnerStatus
    occurred_at: datetime


class EventInviteBounced(BaseModel):
    event_id: str
    event_type: Literal["invite.bounced"]
    org_id: str
    occurred_at: datetime
    data: LearnerEventData


class EventLearnerCertified(BaseModel):
    event_id: str
    event_type: Literal["learner.certified"]
    org_id: str
    occurred_at: datetime
    data: LearnerEventData


class EventLearnerExpired(BaseModel):
    event_id: str
    event_type: Literal["learner.expired"]
    org_id: str
    occurred_at: datetime
    data: LearnerEventData


class EventLearnerExpiring(BaseModel):
    event_id: str
    event_type: Literal["learner.expiring"]
    org_id: str
    occurred_at: datetime
    data: LearnerEventData


class EventLearnerInvited(BaseModel):
    event_id: str
    event_type: Literal["learner.invited"]
    org_id: str
    occurred_at: datetime
    data: LearnerEventData


class EventLearnerRemoved(BaseModel):
    event_id: str
    event_type: Literal["learner.removed"]
    org_id: str
    occurred_at: datetime
    data: LearnerEventData


class EventLearnerStarted(BaseModel):
    event_id: str
    event_type: Literal["learner.started"]
    org_id: str
    occurred_at: datetime
    data: LearnerEventData


class EventSeatConsumed(BaseModel):
    event_id: str
    event_type: Literal["seat.consumed"]
    org_id: str
    occurred_at: datetime
    data: dict[str, Any]


class EventSeatFreed(BaseModel):
    event_id: str
    event_type: Literal["seat.freed"]
    org_id: str
    occurred_at: datetime
    data: dict[str, Any]


SeatOrderEventDataStatus: TypeAlias = Literal["paid", "failed", "expired"] | str


class SeatOrderEventData(BaseModel):
    seat_order_id: str
    quantity: int
    status: SeatOrderEventDataStatus


class EventSeatOrderExpired(BaseModel):
    event_id: str
    event_type: Literal["seat_order.expired"]
    org_id: str
    occurred_at: datetime
    data: SeatOrderEventData


class EventSeatOrderFailed(BaseModel):
    event_id: str
    event_type: Literal["seat_order.failed"]
    org_id: str
    occurred_at: datetime
    data: SeatOrderEventData


class EventSeatOrderPaid(BaseModel):
    event_id: str
    event_type: Literal["seat_order.paid"]
    org_id: str
    occurred_at: datetime
    data: SeatOrderEventData


class SeatsLowEventData(BaseModel):
    available: int
    threshold: int


class EventSeatsLow(BaseModel):
    event_id: str
    event_type: Literal["seats.low"]
    org_id: str
    occurred_at: datetime
    data: SeatsLowEventData


class UnknownEvent(BaseModel):
    """An event whose eventType is not in the catalog yet. The catalog only grows, so
    SDKs parse it instead of failing.
    """

    event_id: str
    event_type: str
    org_id: str
    occurred_at: datetime
    data: dict[str, Any]


Event: TypeAlias = Annotated[
    Annotated[EventCertificateRevoked, Tag("certificate.revoked")]
    | Annotated[EventEnrollmentCertified, Tag("enrollment.certified")]
    | Annotated[EventInviteBounced, Tag("invite.bounced")]
    | Annotated[EventLearnerCertified, Tag("learner.certified")]
    | Annotated[EventLearnerExpired, Tag("learner.expired")]
    | Annotated[EventLearnerExpiring, Tag("learner.expiring")]
    | Annotated[EventLearnerInvited, Tag("learner.invited")]
    | Annotated[EventLearnerRemoved, Tag("learner.removed")]
    | Annotated[EventLearnerStarted, Tag("learner.started")]
    | Annotated[EventSeatConsumed, Tag("seat.consumed")]
    | Annotated[EventSeatFreed, Tag("seat.freed")]
    | Annotated[EventSeatOrderExpired, Tag("seat_order.expired")]
    | Annotated[EventSeatOrderFailed, Tag("seat_order.failed")]
    | Annotated[EventSeatOrderPaid, Tag("seat_order.paid")]
    | Annotated[EventSeatsLow, Tag("seats.low")]
    | Annotated[UnknownEvent, Tag(UNKNOWN_VARIANT)],
    Discriminator(
        by_property(
            "eventType",
            "event_type",
            frozenset(
                {
                    "certificate.revoked",
                    "enrollment.certified",
                    "invite.bounced",
                    "learner.certified",
                    "learner.expired",
                    "learner.expiring",
                    "learner.invited",
                    "learner.removed",
                    "learner.started",
                    "seat.consumed",
                    "seat.freed",
                    "seat_order.expired",
                    "seat_order.failed",
                    "seat_order.paid",
                    "seats.low",
                }
            ),
        )
    ),
]


EventType: TypeAlias = (
    Literal[
        "enrollment.certified",
        "seat.consumed",
        "seat.freed",
        "learner.invited",
        "learner.started",
        "learner.certified",
        "learner.expiring",
        "learner.expired",
        "learner.removed",
        "invite.bounced",
        "certificate.revoked",
        "seats.low",
        "seat_order.paid",
        "seat_order.failed",
        "seat_order.expired",
    ]
    | str
)


class ImportOptions(BaseModel):
    course_id: str | None = None
    """The course to invite everyone to. Defaults to the organization's default course.
    """
    validate_only: bool | None = None
    """Check the file and return a preview without inviting anyone."""


class ImportEnrollmentsRequest(BaseModel):
    file: bytes
    """UTF-8 CSV (RFC 4180: quoted fields, `""` escapes, CRLF/LF). Header row required.
    """
    options: ImportOptions | None = None


ImportPreviewRowsItemStatus: TypeAlias = (
    Literal[
        "valid",
        "invalid_email",
        "duplicate_in_file",
        "already_enrolled",
        "already_invited",
    ]
    | str
)


class ImportPreviewRowsItem(BaseModel):
    row_number: int
    email: str
    name: str | None = None
    course_id: str
    status: ImportPreviewRowsItemStatus
    detail: str | None = None


class ImportPreview(BaseModel):
    total_rows: int
    """Rows in the file."""
    valid_rows: int
    """Rows that would be invited."""
    seats_required: int
    """Seats the import would use."""
    seats_available: int
    """Seats available now."""
    rows: list[ImportPreviewRowsItem]
    """Each row's result: `valid`, `invalid_email`, `duplicate_in_file`,
    `already_enrolled` or `already_invited`.
    """


class LearnerCertificate(BaseModel):
    """The learner's current certificate, with its verification and PDF links."""

    certificate_id: str
    issued_at: datetime
    expires_at: datetime
    verify_url: str | None
    pdf_url: str


class LearnerCourse(BaseModel):
    """The course this learner record is for."""

    course_id: str
    title: str


class Learner(BaseModel):
    learner_id: str
    """Unique identifier for the learner. The same as the member's `subjectId`."""
    email: str
    """The learner's email address."""
    name: str | None
    """The learner's full name."""
    external_id: str | None
    """Your own id for the learner, unique within the organization."""
    status: LearnerStatus
    """The learner's training status in this course. One of `not_started` (invited),
    `invite_bounced`, `in_progress`, `compliant`, `expiring_soon` (within 60 days of
    expiry), `expired` or `removed`.
    """
    course: LearnerCourse
    """The course this learner record is for."""
    invited_at: datetime | None
    """When the learner was invited (ISO 8601)."""
    started_at: datetime | None
    """When the learner started training."""
    completed_at: datetime | None
    """When the learner completed the course."""
    due_at: datetime | None
    """When the learner's training is due."""
    certificate: LearnerCertificate | None
    """The learner's current certificate, with its verification and PDF links."""


LearnerBatchUpsertRequestDelivery: TypeAlias = Literal["email", "none"] | str
"""Applies to every item. `email` (default) sends invites; `none` sends nothing."""


class LearnerBatchUpsertRequestItemsItem(BaseModel):
    email: str
    name: str | None = None
    external_id: str | None = None
    course_id: str | None = None


LearnerBatchUpsertRequestSeatPolicy: TypeAlias = Literal["require_available"] | str
"""Applies to every item. `require_available` fails an item when no seat is free."""


class LearnerBatchUpsertRequest(BaseModel):
    items: list[LearnerBatchUpsertRequestItemsItem]
    """Up to 500 learners, each with the same fields as creating one learner."""
    delivery: LearnerBatchUpsertRequestDelivery | None = None
    """Applies to every item. `email` (default) sends invites; `none` sends nothing."""
    seat_policy: LearnerBatchUpsertRequestSeatPolicy | None = None
    """Applies to every item. `require_available` fails an item when no seat is free."""


LearnerCreateRequestDelivery: TypeAlias = Literal["email", "none"] | str
"""`email` (default) sends the invite email. `none` sends nothing and returns `joinUrl`
for you to deliver.
"""


LearnerCreateRequestSeatPolicy: TypeAlias = Literal["require_available"] | str
"""`require_available` fails with `409` when no seat is free."""


class LearnerCreateRequest(BaseModel):
    email: str
    """The learner's email address."""
    name: str | None = None
    """The learner's full name."""
    external_id: str | None = None
    """Your own id for the learner, unique within the organization."""
    course_id: str | None = None
    """The course to invite them to. Defaults to the organization's default course."""
    delivery: LearnerCreateRequestDelivery | None = None
    """`email` (default) sends the invite email. `none` sends nothing and returns
    `joinUrl` for you to deliver.
    """
    seat_policy: LearnerCreateRequestSeatPolicy | None = None
    """`require_available` fails with `409` when no seat is free."""


class LearnerCreatedCertificate(BaseModel):
    certificate_id: str
    issued_at: datetime
    expires_at: datetime
    verify_url: str | None
    pdf_url: str


class LearnerCreatedCourse(BaseModel):
    """The course the learner was invited to."""

    course_id: str
    title: str


LearnerCreatedDelivery: TypeAlias = Literal["email", "none"] | str
"""How the invite was delivered: `email`, or `none` when you deliver it."""


class LearnerCreated(BaseModel):
    learner_id: str
    """Unique identifier for the learner."""
    email: str
    """The learner's email address."""
    name: str | None
    """The learner's full name."""
    external_id: str | None
    """Your own id for the learner."""
    status: LearnerStatus
    """The learner's training status. One of `not_started` (invited), `invite_bounced`,
    `in_progress`, `compliant`, `expiring_soon` (within 60 days of expiry), `expired` or
    `removed`.
    """
    course: LearnerCreatedCourse
    """The course the learner was invited to."""
    invited_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    due_at: datetime | None
    certificate: LearnerCreatedCertificate | None
    delivery: LearnerCreatedDelivery | None = None
    """How the invite was delivered: `email`, or `none` when you deliver it."""
    join_url: str | None = None
    """The invite link, returned once when `delivery` is `none`. Send it to the learner
    yourself.
    """


class LearnerLaunchLink(BaseModel):
    url: str
    """The single-use sign-in URL. Redirect the learner to it right away."""
    expires_at: datetime
    """When the URL stops working, 5 minutes after it was created."""


class LearnerPatch(BaseModel):
    name: str | None = None
    """The learner's full name."""
    external_id: str | None = None
    """Your own id for the learner. Set it to `null` to clear it."""


LearnerRemindAcceptedAction: TypeAlias = Literal["remind"] | str
"""Always `remind`."""


class LearnerRemindAccepted(BaseModel):
    learner_id: str
    """The learner the reminder is for."""
    action: LearnerRemindAcceptedAction
    """Always `remind`."""


LearnerUpsertRequestDelivery: TypeAlias = Literal["email", "none"] | str
"""`email` (default) sends the invite email. `none` sends nothing and returns `joinUrl`
for you to deliver.
"""


LearnerUpsertRequestSeatPolicy: TypeAlias = Literal["require_available"] | str
"""`require_available` fails with `409` when no seat is free."""


class LearnerUpsertRequest(BaseModel):
    email: str
    """The learner's email address."""
    name: str | None = None
    """The learner's full name."""
    course_id: str | None = None
    """The course to invite them to. Defaults to the organization's default course."""
    delivery: LearnerUpsertRequestDelivery | None = None
    """`email` (default) sends the invite email. `none` sends nothing and returns
    `joinUrl` for you to deliver.
    """
    seat_policy: LearnerUpsertRequestSeatPolicy | None = None
    """`require_available` fails with `409` when no seat is free."""


class LearnerWriteResult(BaseModel):
    """Learner (200, already existed) or LearnerCreated (201, created), told apart by
    `created`.
    """

    learner_id: str
    """Unique identifier for the learner. The same as the member's `subjectId`."""
    email: str
    """The learner's email address."""
    name: str | None
    """The learner's full name."""
    external_id: str | None
    """Your own id for the learner, unique within the organization."""
    status: LearnerStatus
    """The learner's training status in this course. One of `not_started` (invited),
    `invite_bounced`, `in_progress`, `compliant`, `expiring_soon` (within 60 days of
    expiry), `expired` or `removed`.
    """
    course: LearnerCourse
    """The course this learner record is for."""
    invited_at: datetime | None
    """When the learner was invited (ISO 8601)."""
    started_at: datetime | None
    """When the learner started training."""
    completed_at: datetime | None
    """When the learner completed the course."""
    due_at: datetime | None
    """When the learner's training is due."""
    certificate: LearnerCertificate | None
    """The learner's current certificate, with its verification and PDF links."""
    created: bool
    """Not on the wire: the SDK sets it from the status, true for 201 (created) and
    false for 200 (already existed).
    """
    delivery: LearnerCreatedDelivery | None = None
    """How the invite was delivered: `email`, or `none` when you deliver it."""
    join_url: str | None = None
    """The invite link, returned once when `delivery` is `none`. Send it to the learner
    yourself.
    """


LearnersExportRequestFormat: TypeAlias = Literal["csv"] | str
"""The file format. Only `csv` today."""


class LearnersExportRequest(BaseModel):
    format: LearnersExportRequestFormat
    """The file format. Only `csv` today."""
    course_id: str | None = None
    """The course to export. Defaults to the organization's default course."""
    status: LearnerStatus | None = None
    """Only export learners with this status."""


class LearnersPage(PageBody[Learner]):
    pass


ListAuditEventsTransition: TypeAlias = (
    Literal[
        "bounce",
        "start",
        "beginAssessment",
        "submitAssessment",
        "certify",
        "revokeCert",
        "archive",
        "unarchive",
        "reinvite",
        "cancelInvite",
    ]
    | str
)


ListAuditEventsType: TypeAlias = (
    Literal[
        "enrollment.transition",
        "organization.updated",
        "organization.closed",
        "organization.reopened",
        "member.role_changed",
        "member.transferred",
        "member.removed",
        "certificate.issued",
        "certificate.revoked",
        "seat.granted",
        "api_client.created",
        "api_client.secret_rotated",
        "api_client.revoked",
        "learner.updated",
        "oauth_grant.created",
        "oauth_grant.revoked",
        "seat_order.created",
        "seat_order.paid",
        "seat_order.failed",
        "learner.launch_link_created",
        "api_client.updated",
        "oauth_grant.updated",
        "organization.created_by_partner",
    ]
    | str
)


ListEnrollmentsArchived: TypeAlias = Literal["true", "false"] | str


ListEnrollmentsInclude: TypeAlias = Literal["priorCertificate"] | str


ListEnrollmentsStatus: TypeAlias = (
    Literal[
        "INVITED",
        "EMAIL_BOUNCED",
        "STARTED",
        "ASSESSMENT_IN_PROGRESS",
        "CERTIFIED",
        "CANCELLED",
        "EXPIRING",
        "EXPIRED",
        "ARCHIVED",
    ]
    | str
)


ListMembersRole: TypeAlias = Literal["admin"] | str


MemberRole: TypeAlias = Literal["admin", "learner"] | str
"""`admin` or `learner`."""


class Member(BaseModel):
    subject_id: str | None
    """Unique identifier for the member. `null` for an older member who can't be
    addressed yet.
    """
    email: str
    """The member's email address."""
    name: str | None
    """The member's full name."""
    role: MemberRole
    """`admin` or `learner`."""
    is_disabled: bool
    """Whether the member's account is disabled."""


MemberListItemRole: TypeAlias = Literal["admin", "learner"] | str


class MemberListItem(BaseModel):
    subject_id: str | None
    email: str
    name: str | None
    role: MemberListItemRole
    is_disabled: bool
    enrollment_subject_id: str | None = None
    holds_invitation: bool | None = None


class MembersPage(PageBody[MemberListItem]):
    pass


OAuthErrorCode: TypeAlias = (
    Literal[
        "invalid_request",
        "invalid_client",
        "invalid_grant",
        "invalid_scope",
        "unsupported_grant_type",
        "slow_down",
        "temporarily_unavailable",
    ]
    | str
)


class OAuthTokenError(BaseModel):
    error: OAuthErrorCode
    error_description: str | None = Field(default=None, alias="error_description")


class Operation(BaseModel):
    name: str
    """Unique identifier for the operation."""
    done: bool
    """Whether the operation has finished."""
    metadata: dict[str, Any] | None = None
    """Progress information, if any."""
    response: Any = None
    """The result, once `done` is `true`."""
    error: Problem | None = None
    """The problem, if the operation failed."""


class OrgEventsPage(PageBody[Event]):
    pass


PartnerStatus: TypeAlias = Literal["active", "suspended"] | str
"""`active` or `suspended`."""


class Partner(BaseModel):
    partner_id: str
    """Unique identifier for the partner account."""
    name: str
    """The partner's name."""
    app_id: str
    """The partner app."""
    status: PartnerStatus
    """`active` or `suspended`."""
    max_child_orgs: int
    """How many organizations the partner can create."""
    child_org_count: int
    """How many it has created."""
    created_at: datetime
    """When it was created (ISO 8601)."""


class PartnerOrganization(BaseModel):
    org_id: str
    name: str
    created_at: datetime
    grant_active: bool


PartnerOrganizationCreateScopesItem: TypeAlias = (
    Literal[
        "enrollments:read",
        "enrollments:write",
        "certificates:read",
        "members:read",
        "audit:read",
        "learners:read",
        "learners:write",
        "compliance:read",
        "seats:purchase",
        "webhooks:manage",
    ]
    | str
)


class PartnerOrganizationCreate(BaseModel):
    name: str
    """The organization's name."""
    admin_email: str
    """The email address of the organization's administrator."""
    admin_name: str | None = None
    """The administrator's full name."""
    scopes: list[PartnerOrganizationCreateScopesItem]
    """The scopes your app gets on the new organization. A subset of your app's scopes.
    """


PartnerOrganizationCreatedGrantScopesItem: TypeAlias = (
    Literal[
        "enrollments:read",
        "enrollments:write",
        "certificates:read",
        "members:read",
        "audit:read",
        "learners:read",
        "learners:write",
        "compliance:read",
        "seats:purchase",
        "webhooks:manage",
    ]
    | str
)


class PartnerOrganizationCreatedGrant(BaseModel):
    """Your app's connection to the organization."""

    grant_id: str
    scopes: list[PartnerOrganizationCreatedGrantScopesItem]


class PartnerOrganizationCreated(BaseModel):
    org_id: str
    """The new organization's id."""
    name: str
    """The organization's name."""
    created_at: datetime
    """When it was created (ISO 8601)."""
    grant: PartnerOrganizationCreatedGrant
    """Your app's connection to the organization."""
    refresh_token: str = Field(alias="refresh_token")
    """Returned only once. Exchange it at `POST /v1/auth/token` for the organization's
    tokens.
    """


class PartnerOrganizationsPage(PageBody[PartnerOrganization]):
    pass


class PaymentMethodConfirmRequest(BaseModel):
    setup_intent_id: str
    """The SetupIntent you confirmed with Stripe.js."""


class PaymentMethodPrepare(BaseModel):
    setup_intent_id: str
    """The Stripe SetupIntent."""
    client_secret: str
    """Confirm the SetupIntent with Stripe.js using this secret."""
    publishable_key: str
    """The Stripe publishable key to load Stripe.js with."""


class PaymentMethodSetup(BaseModel):
    url: str
    """The Stripe-hosted page to send the buyer to."""


class PaymentMethodSetupRequest(BaseModel):
    return_url: str
    """Where Stripe sends the buyer afterwards. Must be https and on your client's
    allowlist.
    """


class SeatOrderFailure(BaseModel):
    code: str
    message: str


SeatOrderPaymentMethod: TypeAlias = (
    Literal["hosted_checkout", "saved_payment_method", "invoice"] | str
)
"""`hosted_checkout`, `saved_payment_method` or `invoice`."""


SeatOrderStatus: TypeAlias = (
    Literal[
        "requires_action",
        "processing",
        "invoiced",
        "paid",
        "failed",
        "expired",
        "refunded",
    ]
    | str
)
"""`requires_action`, `processing`, `invoiced`, `paid`, `failed`, `expired` or
`refunded`.
"""


class SeatOrder(BaseModel):
    seat_order_id: str
    """Unique identifier for the seat order."""
    org_id: str
    """The organization's id."""
    quantity: int
    """Seats ordered."""
    unit_amount: int
    """Price per seat, in the currency's smallest unit."""
    currency: str
    """Three-letter ISO currency code, lowercase."""
    total: int
    """The order total, in the currency's smallest unit."""
    payment_method: SeatOrderPaymentMethod
    """`hosted_checkout`, `saved_payment_method` or `invoice`."""
    status: SeatOrderStatus
    """`requires_action`, `processing`, `invoiced`, `paid`, `failed`, `expired` or
    `refunded`.
    """
    seats_granted: int
    """Seats granted so far."""
    seats_refunded: int
    """Seats refunded through support."""
    failure: SeatOrderFailure | None
    """Why the order failed, with Stripe's decline code when there is one."""
    client_id: str | None
    """The API client that placed the order, if one did."""
    client_reference: str | None
    """Your own reference for the order."""
    checkout_id: str | None
    """The Stripe checkout session, for a hosted checkout."""
    created_at: datetime
    """When it was created (ISO 8601)."""
    updated_at: datetime
    """When it last changed."""
    rev: int
    """The resource's revision. Its strong `ETag` is derived from it."""


class SeatOrderCreateRequestPaymentHostedCheckout(BaseModel):
    method: Literal["hosted_checkout"]
    return_url: str


class SeatOrderCreateRequestPaymentInvoice(BaseModel):
    method: Literal["invoice"]
    days_until_due: int | None = None


class SeatOrderCreateRequestPaymentSavedPaymentMethod(BaseModel):
    method: Literal["saved_payment_method"]
    return_url: str | None = None
    payment_method_id: str | None = None
    expected_total: int | None = None
    currency: str | None = None


class UnknownSeatOrderCreateRequestPayment(BaseModel):
    """A `SeatOrderCreateRequestPayment` of a kind this version of the library doesn't
    know. Its other fields are kept in `model_extra`.
    """

    method: str


SeatOrderCreateRequestPayment: TypeAlias = Annotated[
    Annotated[SeatOrderCreateRequestPaymentHostedCheckout, Tag("hosted_checkout")]
    | Annotated[SeatOrderCreateRequestPaymentInvoice, Tag("invoice")]
    | Annotated[
        SeatOrderCreateRequestPaymentSavedPaymentMethod, Tag("saved_payment_method")
    ]
    | Annotated[UnknownSeatOrderCreateRequestPayment, Tag(UNKNOWN_VARIANT)],
    Discriminator(
        by_property(
            "method",
            "method",
            frozenset({"hosted_checkout", "invoice", "saved_payment_method"}),
        )
    ),
]
"""How to pay: `hosted_checkout` with a `returnUrl`, `saved_payment_method` with the
card's `paymentMethodId`, or `invoice`. A `returnUrl` must be https and on your API
client's allowlist.
"""


class SeatOrderCreateRequest(BaseModel):
    quantity: int
    """Seats to buy."""
    payment: SeatOrderCreateRequestPayment
    """How to pay: `hosted_checkout` with a `returnUrl`, `saved_payment_method` with the
    card's `paymentMethodId`, or `invoice`. A `returnUrl` must be https and on your API
    client's allowlist.
    """
    client_reference: str | None = None
    """Your own reference for the order."""


class SeatOrderCreatedFailure(BaseModel):
    code: str
    message: str


class SeatOrderCreatedNextActionInvoice(BaseModel):
    type: Literal["invoice"]
    hosted_invoice_url: str


class SeatOrderCreatedNextActionRedirect(BaseModel):
    type: Literal["redirect"]
    url: str


class UnknownSeatOrderCreatedNextAction(BaseModel):
    """A `SeatOrderCreatedNextAction` of a kind this version of the library doesn't
    know. Its other fields are kept in `model_extra`.
    """

    type: str


SeatOrderCreatedNextAction: TypeAlias = Annotated[
    Annotated[SeatOrderCreatedNextActionInvoice, Tag("invoice")]
    | Annotated[SeatOrderCreatedNextActionRedirect, Tag("redirect")]
    | Annotated[UnknownSeatOrderCreatedNextAction, Tag(UNKNOWN_VARIANT)],
    Discriminator(by_property("type", "type", frozenset({"invoice", "redirect"}))),
]
"""Where to send the buyer next: a checkout `url` to redirect to, or a hosted invoice.
"""


SeatOrderCreatedStatus: TypeAlias = (
    Literal[
        "requires_action",
        "processing",
        "invoiced",
        "paid",
        "failed",
        "expired",
        "refunded",
    ]
    | str
)
"""The order's status."""


class SeatOrderCreated(BaseModel):
    seat_order_id: str
    """Unique identifier for the seat order."""
    status: SeatOrderCreatedStatus
    """The order's status."""
    next_action: SeatOrderCreatedNextAction | None
    """Where to send the buyer next: a checkout `url` to redirect to, or a hosted
    invoice.
    """
    failure: SeatOrderCreatedFailure | None
    """Why the payment failed, if it did."""


class SeatOrderQuote(BaseModel):
    quantity: int
    """Seats quoted."""
    unit_amount: int
    """Price per seat, in the currency's smallest unit."""
    currency: str
    """Three-letter ISO currency code, lowercase."""
    subtotal: int
    """Price before tax."""
    tax: Any
    """Always `null`: tax is calculated at payment."""
    total: int
    """The quoted total."""
    quote_expires_at: datetime
    """When the quote expires, 15 minutes after it was made."""


class SeatOrderQuoteRequest(BaseModel):
    quantity: int
    """Seats to quote."""
    currency: str | None = None
    """The currency you expect to be charged in. It must match the organization's."""


class SeatOrdersPage(PageBody[SeatOrder]):
    pass


class SeatsInventoryByState(BaseModel):
    """Seats by internal state. Prefer `purchased`, `assigned` and `available`."""

    unused: int = Field(alias="UNUSED")
    assigned: int = Field(alias="ASSIGNED")
    accepted: int = Field(alias="ACCEPTED")
    revoked: int = Field(alias="REVOKED")
    free: int = Field(alias="FREE")
    refunded: int = Field(alias="REFUNDED")


class SeatsInventory(BaseModel):
    total: int
    """All seats on record."""
    used: int
    """Seats in use."""
    available: int
    """Seats a new invite can use now."""
    purchased: int | None = None
    """Seats the organization holds and hasn't been refunded for, including a trial
    seat.
    """
    assigned: int | None = None
    """Seats held by an invited or enrolled learner."""
    by_state: SeatsInventoryByState
    """Seats by internal state. Prefer `purchased`, `assigned` and `available`."""


class TestDelivery(BaseModel):
    """The body of a :test delivery. It is not an event envelope; its x-tmh-event-id is
    a UUID.
    """

    subscription_id: str
    """The subscription that was tested."""
    test: bool
    """Always true."""


TokenIntrospectionActorType: TypeAlias = Literal["user", "client"] | str
"""`client` for an API client or partner app, `user` for a person."""


TokenIntrospectionMode: TypeAlias = Literal["test", "live"] | str


TokenIntrospectionScopesItem: TypeAlias = (
    Literal[
        "me",
        "enrollments:read",
        "enrollments:write",
        "members:read",
        "members:admin",
        "certificates:read",
        "certificates:write",
        "billing:write",
        "org:admin",
        "audit:read",
        "scim",
        "support:write",
        "learners:read",
        "learners:write",
        "compliance:read",
        "seats:purchase",
        "webhooks:manage",
        "partner:orgs:read",
        "partner:orgs:write",
    ]
    | str
)


class TokenIntrospection(BaseModel):
    actor_type: TokenIntrospectionActorType
    """`client` for an API client or partner app, `user` for a person."""
    client_id: str | None
    """The API client or partner app the token belongs to."""
    subject_id: str | None
    """The person the token belongs to, for a user token."""
    org_id: str | None
    """The organization the token is bound to, if any."""
    scopes: list[TokenIntrospectionScopesItem]
    """The scopes the token holds."""
    mode: TokenIntrospectionMode | None
    """`test` for a Sandbox client, `live` otherwise."""
    expires_at: datetime | None
    """When the token expires (ISO 8601)."""


class WebhookSubscription(BaseModel):
    subscription_id: str
    """Unique identifier for the subscription."""
    endpoint_url: str
    """The HTTPS URL events are delivered to."""
    event_types: list[EventType]
    """The event types delivered."""
    enabled: bool
    """Whether deliveries are on."""
    description: str | None
    """Your description of the subscription."""
    seats_low_threshold: int
    """Send `seats.low` when available seats drop to this number. Defaults to 5."""
    secret_key_id: str
    """Identifies the signing secret. Sent as `x-tmh-key-id`."""
    created_at: datetime
    """When it was created (ISO 8601)."""
    rev: int
    """The resource's revision. Its strong `ETag` is derived from it."""


class WebhookSubscriptionCreate(BaseModel):
    endpoint_url: str
    """The HTTPS URL to deliver events to."""
    event_types: list[EventType]
    """The event types to deliver."""
    description: str | None = None
    """A description for your own reference."""
    seats_low_threshold: int | None = None
    """Send `seats.low` when available seats drop to this number. Defaults to 5."""


class WebhookSubscriptionCreated(BaseModel):
    subscription_id: str
    """Unique identifier for the subscription."""
    endpoint_url: str
    """The HTTPS URL events are delivered to."""
    event_types: list[EventType]
    """The event types delivered."""
    enabled: bool
    """Whether deliveries are on."""
    description: str | None
    seats_low_threshold: int
    secret_key_id: str
    """Identifies the signing secret."""
    created_at: datetime
    rev: int
    secret: str
    """The signing secret. Returned only once: store it now."""


class WebhookSubscriptionPatch(BaseModel):
    endpoint_url: str | None = None
    """The HTTPS URL to deliver events to."""
    event_types: list[EventType] | None = None
    """The event types to deliver."""
    enabled: bool | None = None
    """Turn deliveries on or off."""
    description: str | None = None
    """A description for your own reference."""
    seats_low_threshold: int | None = None
    """Send `seats.low` when available seats drop to this number."""


class WebhookSubscriptionsPage(PageBody[WebhookSubscription]):
    pass
