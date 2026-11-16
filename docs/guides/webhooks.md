# Webhooks

A Webhook subscription sends Events to your HTTPS endpoint as they happen.
Each Delivery is a signed POST of one Event. Your endpoint verifies the
signature, handles the Event and answers 2xx; a Delivery that fails is
retried until it succeeds or is dead-lettered.

Samples assume a `client` created as in
[Getting started](getting-started.md#3-make-your-first-call).

## Create a Webhook subscription

Subscribe an endpoint to the Event types you want. Managing subscriptions
needs the `webhooks:manage` Scope.

<!-- sample: webhook-subscription-create -->
```python
subscription = client.webhook_subscriptions.create(
    endpoint_url="https://hooks.example.com/webhooks/tmh",
    event_types=["learner.certified", "learner.expiring"],
    description="HR sync",
)
signing_secrets.save(subscription.subscription_id, subscription.secret)
print(subscription.subscription_id, subscription.secret_key_id)
```

The response carries the subscription's Signing secret in `secret`, and
only this once: store it now, in a secret manager (`signing_secrets` stands
in for yours). Your endpoint needs it to verify Deliveries.
`webhook_subscriptions.list`, `retrieve`, `update` and `delete` manage
subscriptions later; `update` needs `if_match` (see
[Conditional requests](conditional-requests.md)).

## Verify a Delivery

`Webhook.construct_event` verifies a Delivery and returns its Event, or a
`TestDelivery` (from `teachmehipaa.types`, like every model). It needs
three things exactly as they arrived:

1. **The raw body.** Parsed and re-serialized JSON never verifies, so read
   the body as bytes before anything parses it.
2. **The headers.** A dict works, and so do Flask's, Starlette's and
   Django's `request.headers`.
3. **The request path, with its query string, or the full URL.** The
   signature covers the path the Delivery was sent to, so a verifier that
   drops the path, or its query string, rejects every Delivery.

It also takes the Signing secret. Deliveries signed more than 5 minutes
from your clock, in either direction, are rejected. Verification raises
`WebhookSignatureError` with a `code` saying which check failed:
`missing_header`, `invalid_timestamp`, `timestamp_outside_tolerance`,
`body_hash_mismatch` or `signature_mismatch`. Answer it with 400.

Event types this version doesn't know arrive as an `UnknownEvent`, so new
types never break your handler. The same Event can arrive more than once,
so make your handling idempotent, keyed by `event.event_id`.

`Webhook` needs only the Signing secret, never API credentials, so a
handler can import it without creating a client. It is also on the clients
as `TeachMeHipaa.webhooks`.

### Flask

Read the body with `request.get_data()`. `request.full_path` always ends in
`?`, even with no query string, so strip it:

<!-- sample: webhook-flask -->
```python
import os

from flask import Flask, request

from teachmehipaa import Webhook, WebhookSignatureError
from teachmehipaa.types import TestDelivery

app = Flask(__name__)


@app.post("/webhooks/tmh")
def tmh_webhook() -> tuple[str, int]:
    try:
        event = Webhook.construct_event(
            request.get_data(),
            request.headers,
            os.environ["TMH_WEBHOOK_SECRET"],
            request.full_path.removesuffix("?"),
        )
    except WebhookSignatureError as error:
        return error.code, 400
    if isinstance(event, TestDelivery):
        return "test received", 200
    return f"received {event.event_type}", 200
```

### FastAPI

With FastAPI (or Starlette), read `await request.body()` and pass the full
`request.url`, which keeps any mount path and the query string:

<!-- sample: webhook-fastapi -->
```python
import os

from fastapi import FastAPI, Request, Response

from teachmehipaa import Webhook, WebhookSignatureError
from teachmehipaa.types import TestDelivery

app = FastAPI()


@app.post("/webhooks/tmh")
async def tmh_webhook(request: Request) -> Response:
    try:
        event = Webhook.construct_event(
            await request.body(),
            request.headers,
            os.environ["TMH_WEBHOOK_SECRET"],
            str(request.url),
        )
    except WebhookSignatureError as error:
        return Response(error.code, status_code=400)
    if isinstance(event, TestDelivery):
        return Response("test received")
    return Response(f"received {event.event_type}")
```

### Django

Use `request.body` and `request.get_full_path()`, and exempt the view from
CSRF checks, since the signature authenticates the request:

<!-- sample: webhook-django -->
```python
import os

from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from teachmehipaa import Webhook, WebhookSignatureError
from teachmehipaa.types import TestDelivery


@csrf_exempt
@require_POST
def tmh_webhook(request: HttpRequest) -> HttpResponse:
    try:
        event = Webhook.construct_event(
            request.body,
            request.headers,
            os.environ["TMH_WEBHOOK_SECRET"],
            request.get_full_path(),
        )
    except WebhookSignatureError as error:
        return HttpResponse(error.code, status=400)
    if isinstance(event, TestDelivery):
        return HttpResponse("test received")
    return HttpResponse(f"received {event.event_type}")
```

### Behind a proxy

If a proxy or load balancer rewrites the path before your app sees it, pass
the path the Delivery was sent to, as registered in `endpoint_url`, rather
than the one your framework reports.

## Test deliveries

`webhook_subscriptions.test` sends a signed Test delivery to the
subscription's endpoint, to check your verifier end to end. It carries no
Event: `construct_event` returns a `TestDelivery` with the
`subscription_id`, which your handler should answer with 2xx, as the
handlers above do.

The call returns an Operation that finishes once your endpoint has
answered; `wait()` for it and read the outcome from `response`:

<!-- sample: webhook-test-delivery -->
```python
from teachmehipaa import WebhookDeliveryFailed, WebhookDeliverySent

operation = client.webhook_subscriptions.test("whs_01JD8K2M4N6P8R0T2V4X6Z8B0D")
result = operation.wait(timeout=60).response
if isinstance(result, WebhookDeliverySent):
    print("endpoint answered", result.response_status)
elif isinstance(result, WebhookDeliveryFailed):
    print("delivery failed:", result.reason)
```

`webhook_subscriptions.redrive` delivers a subscription's failed Events
again, and returns the same kind of Operation. A result's `tag` is `sent`,
`failed` or `settled` (the Delivery had already ended); handle tags you
don't recognize, since more may be added.

## Sign test Deliveries yourself

To test your handler without TeachMeHIPAA, sign a payload the way
TeachMeHIPAA does with `Webhook.generate_test_headers`. It takes the body,
the Signing secret and the path, and returns the headers to send with the
body:

<!-- sample: webhook-test-headers -->
```python
import json

from teachmehipaa import Webhook
from teachmehipaa.types import TestDelivery

payload = json.dumps(
    {
        "eventId": "evt_01JD8M",
        "eventType": "learner.certified",
        "orgId": "org_acme",
        "occurredAt": "2026-11-15T12:00:00.000Z",
        "data": {
            "learnerId": "sub_01JD80AB2C3D4E5F6G7H8J9K0M",
            "email": "ana@example.com",
            "externalId": "hr-123",
            "courseId": "hipaa-2026",
            "status": "certified",
            "occurredAt": "2026-11-15T12:00:00.000Z",
        },
    }
)
headers = Webhook.generate_test_headers(payload, "test-signing-secret", "/webhooks/tmh")

event = Webhook.construct_event(
    payload, headers, "test-signing-secret", "/webhooks/tmh"
)
if not isinstance(event, TestDelivery):
    print(event.event_type)
```

[Testing](testing.md#test-your-webhook-handler) shows this inside a test
of a Flask handler.
