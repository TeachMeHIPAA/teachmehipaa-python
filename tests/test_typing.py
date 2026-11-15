"""Static typing of union variants, checked by mypy (`files` includes
`tests/`). `assert_type` does nothing at runtime, so these also run as
ordinary tests on parsed values."""

from typing import Literal

from pydantic import TypeAdapter
from typing_extensions import assert_type

from teachmehipaa.types import (
    AuditEventActor,
    AuditEventActorUser,
    Event,
    EventLearnerCertified,
    EventSeatConsumed,
    PaymentMethodSavedByApiClient,
    SeatOrderCreatedNextAction,
    SeatOrderCreatedNextActionRedirect,
    SeatOrderCreateRequestPaymentInvoiceParam,
    UnknownAuditEventActor,
    UnknownEvent,
    UnknownSeatOrderCreatedNextAction,
)
from tests.fake_api import LEARNER_JSON, ORG_ID

EVENTS: TypeAdapter[Event] = TypeAdapter(Event)
ACTORS: TypeAdapter[AuditEventActor] = TypeAdapter(AuditEventActor)
NEXT_ACTIONS: TypeAdapter[SeatOrderCreatedNextAction] = TypeAdapter(
    SeatOrderCreatedNextAction
)

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


def redirect_url(action: SeatOrderCreatedNextAction) -> str | None:
    if isinstance(action, UnknownSeatOrderCreatedNextAction):
        return None
    if action.type == "redirect":
        assert_type(action, SeatOrderCreatedNextActionRedirect)
        return action.url
    return None


def test_nested_unions_narrow_on_their_tag_too() -> None:
    redirect = {"type": "redirect", "url": "https://pay.example/so_1"}

    assert redirect_url(NEXT_ACTIONS.validate_python(redirect)) == (
        "https://pay.example/so_1"
    )
    actor = ACTORS.validate_python({"type": "user", "subjectId": "sub_admin"})
    assert isinstance(actor, AuditEventActorUser)
    assert_type(actor.type, Literal["user"])
    unknown_actor = ACTORS.validate_python({"type": "robot"})
    assert isinstance(unknown_actor, UnknownAuditEventActor)
    assert_type(unknown_actor.type, str)


def test_a_saved_by_variant_is_typed_as_its_tag() -> None:
    saved_by = PaymentMethodSavedByApiClient(type="api_client", name="HR sync")

    assert_type(saved_by.type, Literal["api_client"])


def test_a_request_variant_requires_its_own_tag() -> None:
    payment: SeatOrderCreateRequestPaymentInvoiceParam = {"method": "invoice"}

    assert payment["method"] == "invoice"
    assert_type(payment["method"], Literal["invoice"])
