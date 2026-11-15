"""Webhook Delivery verification and test-header signing (ADR-0005)."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from pydantic import TypeAdapter

from ._core._errors import WebhookSignatureError
from .types._models import Event, TestDelivery, UnknownEvent

_EVENT: TypeAdapter[Event] = TypeAdapter(Event)

# `datetime.fromisoformat` on Python 3.10 refuses `Z` and fractions that are
# not 3 or 6 digits, both of which the platform's ISO 8601 allows.
_ISO_8601_DATE_TIME = re.compile(
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:\d{2})",
    re.ASCII,
)

_HEX_SHA256 = re.compile(r"[0-9a-f]{64}", re.ASCII)

_RAW_BODY_HINT = (
    "Are you passing the raw request body exactly as received? Parsed and "
    "re-serialized JSON does not verify."
)


def _header(headers: Mapping[str, str], name: str) -> str | None:
    # Framework header objects (Django, Starlette, Werkzeug) look names up
    # case-insensitively; a plain dict needs the scan.
    value = headers.get(name)
    if value is not None:
        return value
    return next((value for key, value in headers.items() if key.lower() == name), None)


def _required_header(headers: Mapping[str, str], name: str) -> str:
    value = _header(headers, name)
    if not value:
        raise WebhookSignatureError(
            "missing_header",
            f"No {name} header found on the Delivery. Are you passing the "
            "request headers as TeachMeHIPAA sent them?",
        )
    return value


def _path_and_query(path: str) -> str:
    # Mirrors the platform signer, which signs the endpoint URL's path and
    # query and takes a "/"-prefixed path as given.
    if path.startswith("/"):
        return path
    url = urlsplit(path)
    if not (url.scheme and url.netloc):
        raise ValueError(
            "path must be the request path (such as '/webhooks/tmh?x=1') or "
            f"the full request URL, got {path!r}"
        )
    query = f"?{url.query}" if url.query else ""
    return f"{url.path or '/'}{query}"


def _parse_timestamp(timestamp: str) -> datetime:
    match = _ISO_8601_DATE_TIME.fullmatch(timestamp)
    try:
        if match is None:
            raise ValueError(timestamp)
        date_time, fraction, offset = match.groups()
        microseconds = (fraction or "").ljust(6, "0")[:6]
        offset = "+00:00" if offset == "Z" else offset
        return datetime.fromisoformat(f"{date_time}.{microseconds}{offset}")
    except ValueError:
        raise WebhookSignatureError(
            "invalid_timestamp",
            f"The x-tmh-timestamp header {timestamp!r} is not an ISO 8601 date-time.",
        ) from None


def _signature(secret: str, signed_path: str, timestamp: str, body_hash: str) -> str:
    # ADR-0005: the key is the Signing secret's UTF-8 bytes. The secret looks
    # like base64, but the platform never decodes it.
    if not secret:
        raise ValueError(
            "secret must be the Webhook subscription's Signing secret; got an "
            "empty value"
        )
    canonical = f"POST\n{signed_path}\n{timestamp}\n{body_hash}"
    return hmac.new(
        secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def _aware(value: datetime | None, name: str) -> datetime | None:
    if value is not None and value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value


def _to_bytes(payload: bytes | str) -> bytes:
    return payload.encode("utf-8") if isinstance(payload, str) else payload


def _format_timestamp(value: datetime) -> str:
    # The platform's format: JavaScript's `Date.toISOString()`, always UTC
    # with milliseconds.
    utc = value.astimezone(timezone.utc)
    return f"{utc:%Y-%m-%dT%H:%M:%S}.{utc.microsecond // 1000:03d}Z"


def _parse(body: bytes) -> Event | UnknownEvent | TestDelivery:
    # A Test delivery is not an Event envelope (ADR-0005), so it never
    # reaches the Event union, whose fallback would reject it.
    data = json.loads(body)
    if isinstance(data, dict) and data.get("test") is True and "subscriptionId" in data:
        return TestDelivery.model_validate(data)
    return _EVENT.validate_python(data)


class Webhook:
    """Verifies Deliveries and signs payloads for your own tests. Needs only
    the Signing secret, never API credentials."""

    @staticmethod
    def construct_event(
        payload: bytes | str,
        headers: Mapping[str, str],
        secret: str,
        path: str,
        *,
        tolerance: int = 300,
        received_at: datetime | None = None,
    ) -> Event | UnknownEvent | TestDelivery:
        """Verify a Delivery and return its Event, or the Test delivery.

        Pass the raw body exactly as received, and the path with its query
        string (or the full URL) the request arrived on: the signature covers
        both. `headers` may be any mapping, such as Django's, Flask's or
        Starlette's `request.headers`. An Event type this version doesn't
        know comes back as an `UnknownEvent`.

        Raises `WebhookSignatureError` when the Delivery fails verification.
        """
        signed_path = _path_and_query(path)
        if not tolerance > 0:
            raise ValueError("tolerance must be a positive number of seconds")
        now = _aware(received_at, "received_at") or datetime.now(timezone.utc)
        signature = _required_header(headers, "x-tmh-signature")
        timestamp = _required_header(headers, "x-tmh-timestamp")
        signed_at = _parse_timestamp(timestamp)

        body = _to_bytes(payload)
        body_hash = hashlib.sha256(body).hexdigest()

        sent_body_hash = _header(headers, "x-tmh-body-hash")
        if sent_body_hash is not None and sent_body_hash != body_hash:
            raise WebhookSignatureError(
                "body_hash_mismatch",
                "The x-tmh-body-hash header does not match the body. " + _RAW_BODY_HINT,
            )

        expected = _signature(secret, signed_path, timestamp, body_hash)
        # `compare_digest` only accepts ASCII strings, hence the format check
        # before it.
        if not (
            _HEX_SHA256.fullmatch(signature)
            and hmac.compare_digest(expected, signature)
        ):
            raise WebhookSignatureError(
                "signature_mismatch",
                "No signature matched the expected signature for this Delivery. "
                f"{_RAW_BODY_HINT} Are you passing the exact request path, with "
                "its query string, that the Delivery was sent to, and the "
                "Webhook subscription's Signing secret?",
            )

        if abs(now - signed_at) > timedelta(seconds=tolerance):
            raise WebhookSignatureError(
                "timestamp_outside_tolerance",
                f"The Delivery's timestamp {timestamp} is more than {tolerance} "
                "seconds from now. Check your server's clock; otherwise the "
                "Delivery is being replayed.",
            )

        return _parse(body)

    @staticmethod
    def generate_test_headers(
        payload: bytes | str,
        secret: str,
        path: str,
        *,
        timestamp: datetime | None = None,
        event_type: str | None = None,
        event_id: str | None = None,
        key_id: str | None = None,
    ) -> dict[str, str]:
        """Return the headers TeachMeHIPAA would send with `payload` to
        `path`, so you can test your handler without a real Delivery.

        `payload` must be the exact body you will send. `timestamp` defaults
        to now.
        """
        signed_at = _aware(timestamp, "timestamp") or datetime.now(timezone.utc)
        formatted = _format_timestamp(signed_at)
        body_hash = hashlib.sha256(_to_bytes(payload)).hexdigest()
        signature = _signature(secret, _path_and_query(path), formatted, body_hash)
        optional = {
            "x-tmh-key-id": key_id,
            "x-tmh-event-type": event_type,
            "x-tmh-event-id": event_id,
        }
        return {
            **{name: value for name, value in optional.items() if value is not None},
            "x-tmh-timestamp": formatted,
            "x-tmh-signature": signature,
            "x-tmh-body-hash": body_hash,
            "content-type": "application/json",
        }
