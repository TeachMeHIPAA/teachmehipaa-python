"""Webhook Delivery verification and test-header signing (ADR-0005)."""

import inspect
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from teachmehipaa import (
    AsyncTeachMeHipaa,
    TeachMeHipaa,
    TeachMeHipaaError,
    Webhook,
    WebhookSignatureError,
    types,
)
from teachmehipaa.types import EventLearnerCertified, UnknownEvent
from tests.fake_api import CLIENT_ID, CLIENT_SECRET

# The shared cross-SDK vector (~/scratch/tmh-sdks/_shared/webhook-vector.json),
# signed by the platform's own signer, not this SDK: `bun platform-sign.ts`
# run in the monorepo calls packages/auth-s2s `signRequest` on
# packages/webhooks `canonicalizeEventBody(envelope)`, and a node:crypto-only
# replica of auth-s2s canonical.ts produced the same hex.
SECRET = "4l28+FYKZo2O57actVGINwR/Xyhzt3OtqCipV81/Zd0="
KEY_ID = "WHSEC-7KQ2-M4XD-9RTB-H3VN"
PATH = "/hooks/tmh?source=teachmehipaa"
EVENT_TIMESTAMP = "2026-11-15T16:31:32.123Z"
EVENT_BODY = (
    '{"data":{"courseId":"hipaa-basics-2026","email":"zoë.müller@example.com",'
    '"externalId":"hr-123","learnerId":"lrn_4h7j2k",'
    '"occurredAt":"2026-11-15T16:31:30.000Z","status":"certified"},'
    '"eventId":"evt_01JCZ8Y2K5V3M7Q9R4T6W8X0AB","eventType":"learner.certified",'
    '"occurredAt":"2026-11-15T16:31:30.000Z","orgId":"org_9f3k2m"}'
)
EVENT_BODY_HASH = "0a849105d2fea53433e3284d0dc6dee83ebccdf6e64088bf34bf3b537b6e640b"
EVENT_SIGNATURE = "c2a0fd14bca6c361c44e84a5b3bf0378b00c49a533636a229c2b6972073b618a"


def event_headers() -> dict[str, str]:
    return {
        "x-tmh-key-id": KEY_ID,
        "x-tmh-timestamp": EVENT_TIMESTAMP,
        "x-tmh-signature": EVENT_SIGNATURE,
        "x-tmh-body-hash": EVENT_BODY_HASH,
        "x-tmh-event-type": "learner.certified",
        "x-tmh-event-id": "evt_01JCZ8Y2K5V3M7Q9R4T6W8X0AB",
        "content-type": "application/json",
    }


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


# What a signer that wrongly base64-decodes the Signing secret produces for
# the same Delivery (the vector's `signatureWithBase64DecodedKey`).
SIGNATURE_WITH_DECODED_KEY = (
    "26c88e3993dc44d1f52949f6bc1a9061c5e3e9c0b12caf04934e2e4ea3814f2d"
)

# The vector's Test delivery, signed the same way: the body the platform's
# `:test` route builds, canonicalized.
TEST_DELIVERY_TIMESTAMP = "2026-11-15T16:40:05.000Z"
TEST_DELIVERY_BODY = '{"subscriptionId":"whs_2b8f4c1d","test":true}'
TEST_DELIVERY_BODY_HASH = (
    "42879a05e13a5dfba51eee07c2fef4814ec6009091f1389a8db4403661ce6a66"
)
TEST_DELIVERY_SIGNATURE = (
    "b7baa3ae58a738d025adf4e27ce7af833ac6085f5cb1cc5fc8ff1addb191c3b9"
)
TEST_DELIVERY_EVENT_ID = "3f1c9a52-7d4e-4b8a-9c21-5e6f7a8b9c0d"


def the_test_delivery_headers() -> dict[str, str]:
    return {
        "x-tmh-key-id": KEY_ID,
        "x-tmh-timestamp": TEST_DELIVERY_TIMESTAMP,
        "x-tmh-signature": TEST_DELIVERY_SIGNATURE,
        "x-tmh-body-hash": TEST_DELIVERY_BODY_HASH,
        "x-tmh-event-type": "learner.certified",
        "x-tmh-event-id": TEST_DELIVERY_EVENT_ID,
        "content-type": "application/json",
    }


def event_headers_without(name: str) -> dict[str, str]:
    return {key: value for key, value in event_headers().items() if key != name}


AT_EVENT_TIME = utc("2026-11-15T16:31:40.000")


def rejection(
    payload: bytes | str,
    headers: dict[str, str],
    secret: str = SECRET,
    path: str = PATH,
    *,
    tolerance: int = 300,
    received_at: datetime = AT_EVENT_TIME,
) -> WebhookSignatureError:
    with pytest.raises(WebhookSignatureError) as caught:
        Webhook.construct_event(
            payload,
            headers,
            secret,
            path,
            tolerance=tolerance,
            received_at=received_at,
        )
    assert isinstance(caught.value, TeachMeHipaaError)
    return caught.value


class TestConstructEvent:
    def test_verifies_a_delivery_signed_by_the_platform_and_returns_its_event(
        self,
    ) -> None:
        event = Webhook.construct_event(
            EVENT_BODY.encode(),
            event_headers(),
            SECRET,
            PATH,
            received_at=AT_EVENT_TIME,
        )

        assert isinstance(event, EventLearnerCertified)
        assert isinstance(event, EventLearnerCertified)
        assert event.event_id == "evt_01JCZ8Y2K5V3M7Q9R4T6W8X0AB"
        assert isinstance(event, EventLearnerCertified)
        assert event.org_id == "org_9f3k2m"
        assert event.occurred_at == utc("2026-11-15T16:31:30.000")
        assert event.data.learner_id == "lrn_4h7j2k"
        assert event.data.email == "zoë.müller@example.com"
        assert event.data.external_id == "hr-123"
        assert event.data.course_id == "hipaa-basics-2026"
        assert event.data.status == "certified"

    def test_rejects_a_tampered_body(self) -> None:
        tampered = EVENT_BODY.replace("hr-123", "hr-124")

        error = rejection(tampered, event_headers())

        assert error.code == "body_hash_mismatch"
        assert "raw request body" in error.message

    def test_rejects_a_tampered_body_without_a_body_hash_header(self) -> None:
        tampered = EVENT_BODY.replace("hr-123", "hr-124")

        error = rejection(tampered, event_headers_without("x-tmh-body-hash"))

        assert error.code == "signature_mismatch"

    def test_rejects_a_delivery_verified_against_the_wrong_path(self) -> None:
        error = rejection(EVENT_BODY, event_headers(), path="/hooks/tmh")

        assert error.code == "signature_mismatch"
        assert "exact request path" in error.message

    def test_rejects_a_delivery_verified_with_the_wrong_signing_secret(
        self,
    ) -> None:
        error = rejection(
            EVENT_BODY,
            event_headers(),
            secret="Zm9vYmFyYmF6cXV4cXV1eGNvcmdlZ3JhdWx0Z2FycGx5",
        )

        assert error.code == "signature_mismatch"

    def test_rejects_a_signature_made_with_the_base64_decoded_signing_secret(
        self,
    ) -> None:
        headers = {**event_headers(), "x-tmh-signature": SIGNATURE_WITH_DECODED_KEY}

        error = rejection(EVENT_BODY, headers)

        assert error.code == "signature_mismatch"

    @pytest.mark.parametrize("signature", ["", "not-hex", "é" * 64])
    def test_rejects_a_malformed_signature(self, signature: str) -> None:
        headers = {**event_headers(), "x-tmh-signature": signature}

        error = rejection(EVENT_BODY, headers)

        assert error.code in {"missing_header", "signature_mismatch"}

    @pytest.mark.parametrize("name", ["x-tmh-signature", "x-tmh-timestamp"])
    def test_rejects_a_delivery_without_a_required_header(self, name: str) -> None:
        error = rejection(EVENT_BODY, event_headers_without(name))

        assert error.code == "missing_header"
        assert name in error.message

    @pytest.mark.parametrize(
        "timestamp", ["1763224292", "2026-11-15 16:31:32Z", "2026-13-15T16:31:32Z"]
    )
    def test_rejects_a_timestamp_that_is_not_iso_8601(self, timestamp: str) -> None:
        headers = {**event_headers(), "x-tmh-timestamp": timestamp}

        error = rejection(EVENT_BODY, headers)

        assert error.code == "invalid_timestamp"

    def test_signature_errors_never_carry_the_body_or_headers(self) -> None:
        tampered = EVENT_BODY.replace("hr-123", "hr-124")

        error = rejection(tampered, event_headers())

        assert error.body is None
        assert len(error.headers) == 0
        assert "zoë" not in str(error)
        assert error.status is None
        assert error.request_id is None

    def test_rejects_a_delivery_more_than_5_minutes_old(self) -> None:
        error = rejection(
            EVENT_BODY,
            event_headers(),
            received_at=utc("2026-11-15T16:36:32.124"),
        )

        assert error.code == "timestamp_outside_tolerance"

    def test_rejects_a_delivery_more_than_5_minutes_in_the_future(self) -> None:
        error = rejection(
            EVENT_BODY,
            event_headers(),
            received_at=utc("2026-11-15T16:26:32.122"),
        )

        assert error.code == "timestamp_outside_tolerance"

    @pytest.mark.parametrize(
        "received_at", ["2026-11-15T16:36:32.123", "2026-11-15T16:26:32.123"]
    )
    def test_accepts_a_delivery_exactly_5_minutes_off(self, received_at: str) -> None:
        event = Webhook.construct_event(
            EVENT_BODY,
            event_headers(),
            SECRET,
            PATH,
            received_at=utc(received_at),
        )

        assert isinstance(event, EventLearnerCertified)

    def test_honors_a_custom_tolerance_in_seconds(self) -> None:
        error = rejection(
            EVENT_BODY,
            event_headers(),
            tolerance=5,
            received_at=utc("2026-11-15T16:31:40.000"),
        )

        assert error.code == "timestamp_outside_tolerance"

    def test_compares_timestamps_across_utc_offsets(self) -> None:
        event = Webhook.construct_event(
            EVENT_BODY,
            event_headers(),
            SECRET,
            PATH,
            received_at=datetime.fromisoformat("2026-11-15T11:31:40.000-05:00"),
        )

        assert isinstance(event, EventLearnerCertified)

    def test_checks_the_signature_before_the_timestamp(self) -> None:
        # A forgery must never be reported as merely late.
        tampered = EVENT_BODY.replace("hr-123", "hr-124")

        error = rejection(
            tampered,
            event_headers_without("x-tmh-body-hash"),
            received_at=utc("2027-01-01T00:00:00.000"),
        )

        assert error.code == "signature_mismatch"

    @pytest.mark.parametrize("tolerance", [0, -1, float("nan")])
    def test_refuses_a_tolerance_that_is_not_positive(self, tolerance: int) -> None:
        with pytest.raises(ValueError, match="tolerance"):
            Webhook.construct_event(
                EVENT_BODY, event_headers(), SECRET, PATH, tolerance=tolerance
            )

    def test_refuses_a_naive_received_at(self) -> None:
        with pytest.raises(ValueError, match="timezone"):
            Webhook.construct_event(
                EVENT_BODY,
                event_headers(),
                SECRET,
                PATH,
                received_at=datetime(2026, 11, 15, 16, 31, 40),
            )

    def test_refuses_an_empty_signing_secret(self) -> None:
        with pytest.raises(ValueError, match="Signing secret"):
            Webhook.construct_event(EVENT_BODY, event_headers(), "", PATH)

    def test_returns_a_test_delivery_as_its_own_type(self) -> None:
        delivery = Webhook.construct_event(
            TEST_DELIVERY_BODY,
            the_test_delivery_headers(),
            SECRET,
            PATH,
            received_at=utc("2026-11-15T16:40:06.000"),
        )

        assert isinstance(delivery, types.TestDelivery)
        assert delivery.subscription_id == "whs_2b8f4c1d"
        assert delivery.test is True

    def test_returns_an_event_of_a_type_not_in_the_catalog_as_an_unknown_event(
        self,
    ) -> None:
        body = (
            '{"data":{"badge":"gold","learnerId":"lrn_4h7j2k"},'
            '"eventId":"evt_01JCZ9000000000000000000AB",'
            '"eventType":"learner.promoted",'
            '"occurredAt":"2026-11-15T16:31:30.000Z","orgId":"org_9f3k2m"}'
        )
        headers = Webhook.generate_test_headers(
            body, SECRET, PATH, timestamp=utc("2026-11-15T16:31:32.123")
        )

        event = Webhook.construct_event(
            body, headers, SECRET, PATH, received_at=AT_EVENT_TIME
        )

        assert isinstance(event, UnknownEvent)
        assert event.event_type == "learner.promoted"
        assert event.data == {"badge": "gold", "learnerId": "lrn_4h7j2k"}

    def test_accepts_a_framework_header_object_and_any_header_case(self) -> None:
        # httpx.Headers stands in for Django's, Werkzeug's and Starlette's
        # case-insensitive header mappings.
        headers = httpx.Headers(
            {
                "X-TMH-Timestamp": EVENT_TIMESTAMP,
                "X-TMH-Signature": EVENT_SIGNATURE,
            }
        )

        event = Webhook.construct_event(
            EVENT_BODY.encode(), headers, SECRET, PATH, received_at=AT_EVENT_TIME
        )

        assert isinstance(event, EventLearnerCertified)
        assert event.event_id == "evt_01JCZ8Y2K5V3M7Q9R4T6W8X0AB"

    def test_accepts_a_plain_dict_with_mixed_case_header_names(self) -> None:
        headers = {
            "X-Tmh-Timestamp": EVENT_TIMESTAMP,
            "X-TMH-SIGNATURE": EVENT_SIGNATURE,
            "X-Tmh-Body-Hash": EVENT_BODY_HASH,
        }

        event = Webhook.construct_event(
            EVENT_BODY, headers, SECRET, PATH, received_at=AT_EVENT_TIME
        )

        assert isinstance(event, EventLearnerCertified)

    def test_accepts_the_full_request_url_in_place_of_the_path(self) -> None:
        event = Webhook.construct_event(
            EVENT_BODY,
            event_headers(),
            SECRET,
            "https://partner.example.com/hooks/tmh?source=teachmehipaa",
            received_at=AT_EVENT_TIME,
        )

        assert isinstance(event, EventLearnerCertified)

    def test_refuses_a_path_that_is_neither_a_path_nor_a_url(self) -> None:
        with pytest.raises(ValueError, match="request path"):
            Webhook.construct_event(
                EVENT_BODY, event_headers(), SECRET, "hooks/tmh?source=teachmehipaa"
            )


class TestGenerateTestHeaders:
    def test_produces_the_headers_the_platform_sent_for_the_vectors_event(
        self,
    ) -> None:
        headers = Webhook.generate_test_headers(
            EVENT_BODY,
            SECRET,
            PATH,
            timestamp=utc("2026-11-15T16:31:32.123"),
            event_type="learner.certified",
            event_id="evt_01JCZ8Y2K5V3M7Q9R4T6W8X0AB",
            key_id=KEY_ID,
        )

        assert headers == event_headers()

    def test_produces_the_headers_the_platform_sent_for_the_vectors_test_delivery(
        self,
    ) -> None:
        headers = Webhook.generate_test_headers(
            TEST_DELIVERY_BODY.encode(),
            SECRET,
            "https://partner.example.com/hooks/tmh?source=teachmehipaa",
            timestamp=datetime.fromisoformat("2026-11-15T17:40:05+01:00"),
            event_type="learner.certified",
            event_id=TEST_DELIVERY_EVENT_ID,
            key_id=KEY_ID,
        )

        assert headers == the_test_delivery_headers()

    def test_leaves_out_the_identifying_headers_it_was_not_given(self) -> None:
        headers = Webhook.generate_test_headers(
            TEST_DELIVERY_BODY,
            SECRET,
            PATH,
            timestamp=utc("2026-11-15T16:40:05.000"),
        )

        assert headers == {
            "x-tmh-timestamp": TEST_DELIVERY_TIMESTAMP,
            "x-tmh-signature": TEST_DELIVERY_SIGNATURE,
            "x-tmh-body-hash": TEST_DELIVERY_BODY_HASH,
            "content-type": "application/json",
        }

    def test_produces_headers_that_construct_event_accepts_now(self) -> None:
        headers = Webhook.generate_test_headers(TEST_DELIVERY_BODY, SECRET, PATH)

        delivery = Webhook.construct_event(TEST_DELIVERY_BODY, headers, SECRET, PATH)

        assert isinstance(delivery, types.TestDelivery)
        assert delivery.subscription_id == "whs_2b8f4c1d"

    def test_refuses_a_naive_timestamp(self) -> None:
        with pytest.raises(ValueError, match="timezone"):
            Webhook.generate_test_headers(
                TEST_DELIVERY_BODY,
                SECRET,
                PATH,
                timestamp=datetime(2026, 11, 15, 16, 40, 5),
            )


@pytest.mark.parametrize("client_class", [TeachMeHipaa, AsyncTeachMeHipaa])
def test_webhooks_are_reachable_from_either_client_without_a_request(
    client_class: type[TeachMeHipaa] | type[AsyncTeachMeHipaa],
) -> None:
    client = client_class(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

    assert client.webhooks is Webhook
    assert client_class.webhooks is Webhook
    event = client.webhooks.construct_event(
        EVENT_BODY, event_headers(), SECRET, PATH, received_at=AT_EVENT_TIME
    )
    assert isinstance(event, EventLearnerCertified)


class TestTheVendoredIrSigningRecipe:
    """The verifier hardcodes ADR-0005's recipe. If the IR ever describes a
    different one, these fail and the verifier must change with it."""

    @pytest.fixture
    def signing(self) -> dict[str, object]:
        ir_path = Path(__file__).parent.parent / "openapi" / "sdk-ir.json"
        signing: dict[str, object] = json.loads(ir_path.read_text())["events"][
            "signing"
        ]
        return signing

    def test_is_the_recipe_this_sdk_verifies(self, signing: dict[str, object]) -> None:
        assert signing == {
            "algorithm": "hmacSha256Hex",
            "canonical": {
                "parts": [
                    {"kind": "literal", "value": "POST"},
                    {"kind": "pathAndQuery"},
                    {"kind": "header", "name": "x-tmh-timestamp"},
                    {"kind": "bodySha256Hex"},
                ],
                "separator": "\n",
            },
            "headers": {
                "bodyHash": "x-tmh-body-hash",
                "eventId": "x-tmh-event-id",
                "eventType": "x-tmh-event-type",
                "keyId": "x-tmh-key-id",
                "signature": "x-tmh-signature",
                "timestamp": "x-tmh-timestamp",
            },
            "key": "secretUtf8",
            "timestampFormat": "iso8601",
            "toleranceSeconds": 300,
        }

    def test_default_tolerance_is_the_irs(self, signing: dict[str, object]) -> None:
        tolerance = inspect.signature(Webhook.construct_event).parameters["tolerance"]

        assert tolerance.default == signing["toleranceSeconds"]

    def test_generated_headers_are_the_irs(self, signing: dict[str, object]) -> None:
        headers = Webhook.generate_test_headers(
            EVENT_BODY,
            SECRET,
            PATH,
            event_type="learner.certified",
            event_id="evt_01JCZ8Y2K5V3M7Q9R4T6W8X0AB",
            key_id=KEY_ID,
        )
        ir_headers = signing["headers"]
        assert isinstance(ir_headers, dict)

        assert set(headers) == {*ir_headers.values(), "content-type"}
