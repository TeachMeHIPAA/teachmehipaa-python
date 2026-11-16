"""Static typing of union variants, checked by mypy (`files` includes
`tests/`). `assert_type` does nothing at runtime, so these also run as
ordinary tests on parsed values."""

from typing import Literal

from pydantic import TypeAdapter
from typing_extensions import assert_type

from teachmehipaa.types import (
    AuditEvent,
    AuditEventActor,
    AuditEventActorClient,
    AuditEventActorUser,
    AuditEventMemberRemoved,
    EnrollmentsBatchRequestSelectFilterFilterParam,
    EnrollmentsBatchRequestSelectFilterParam,
    Event,
    EventLearnerCertified,
    EventSeatConsumed,
    UnknownAuditEventActor,
    UnknownEvent,
)
from tests.fake_api import LEARNER_JSON, ORG_ID

EVENTS: TypeAdapter[Event] = TypeAdapter(Event)
AUDIT_EVENTS: TypeAdapter[AuditEvent] = TypeAdapter(AuditEvent)
ACTORS: TypeAdapter[AuditEventActor] = TypeAdapter(AuditEventActor)

CERTIFIED = {
    "eventId": "evt_01",
    "eventType": "learner.certified",
    "orgId": ORG_ID,
    "occurredAt": "2026-11-15T16:31:30.000Z",
    "data": {
        "learnerId": LEARNER_JSON["learnerId"],
        "email": LEARNER_JSON["email"],
        "externalId": LEARNER_JSON["externalId"],
        "courseId": "hipaa-2026",
        "status": "certified",
        "occurredAt": "2026-11-15T16:31:30.000Z",
    },
}


def test_a_variants_discriminator_is_typed_as_its_tag() -> None:
    event = EVENTS.validate_python(CERTIFIED)

    assert isinstance(event, EventLearnerCertified)
    assert_type(event.event_type, Literal["learner.certified"])
    assert event.event_type == "learner.certified"


def test_the_unknown_fallback_keeps_an_open_string() -> None:
    event = EVENTS.validate_python({**CERTIFIED, "eventType": "course.retired"})

    assert isinstance(event, UnknownEvent)
    assert_type(event.event_type, str)
    assert event.event_type == "course.retired"


def certified_learner_id(event: Event) -> str | None:
    # The fallback's discriminator is any string, so it could equal a known
    # tag; once it is ruled out, comparing the tag alone narrows the union.
    if isinstance(event, UnknownEvent):
        return None
    if event.event_type == "learner.certified":
        assert_type(event, EventLearnerCertified)
        return event.data.learner_id
    return None


def test_comparing_the_tag_narrows_an_event_to_its_variant() -> None:
    assert (
        certified_learner_id(EVENTS.validate_python(CERTIFIED))
        == (LEARNER_JSON["learnerId"])
    )
    seat = EVENTS.validate_python({**CERTIFIED, "eventType": "seat.consumed"})
    assert isinstance(seat, EventSeatConsumed)
    assert certified_learner_id(seat) is None


def acting_subject_id(actor: AuditEventActor) -> str | None:
    if isinstance(actor, UnknownAuditEventActor):
        return None
    if actor.type == "user":
        assert_type(actor, AuditEventActorUser)
        return actor.subject_id
    return None


def test_nested_unions_narrow_on_their_tag_too() -> None:
    removed = AUDIT_EVENTS.validate_python(
        {
            "eventId": "aud_1",
            "at": "2026-11-10T08:00:00Z",
            "type": "member.removed",
            "actorSubjectId": "sub_admin",
            "actor": {"type": "user", "subjectId": "sub_admin"},
            "subjectId": "sub_gone",
            "wasAdmin": False,
        }
    )

    assert isinstance(removed, AuditEventMemberRemoved)
    assert acting_subject_id(removed.actor) == "sub_admin"
    unknown_actor = ACTORS.validate_python({"type": "robot"})
    assert isinstance(unknown_actor, UnknownAuditEventActor)
    assert_type(unknown_actor.type, str)
    assert acting_subject_id(unknown_actor) is None


def test_a_variant_parsed_on_its_own_is_typed_as_its_tag() -> None:
    actor = AuditEventActorClient.model_validate(
        {"type": "client", "clientId": "cli_1"}
    )

    assert_type(actor.type, Literal["client"])


def test_a_request_variant_requires_its_own_member() -> None:
    select: EnrollmentsBatchRequestSelectFilterParam = {
        "filter": {"course_id": "hipaa-essentials"}
    }

    assert_type(select["filter"], EnrollmentsBatchRequestSelectFilterFilterParam)
    assert select["filter"] == {"course_id": "hipaa-essentials"}
