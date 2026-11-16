# Webhooks

A Webhook subscription POSTs Events to your HTTPS endpoint as they happen.
Each POST is a Delivery: one Event, signed with the subscription's Signing
secret. Your view checks the signature, handles the Event and answers 2xx.
TeachMeHIPAA retries a failed Delivery until it succeeds or lands in the
dead letters. Samples use a `client` built as in the
[Quickstart](quickstart.md#make-a-request).

## Subscribe an endpoint

Managing subscriptions takes the `webhooks:manage` Scope.

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

The response holds the Signing secret in `secret`, and no later response
will. Put it in your secret manager right away (`signing_secrets` stands in
for yours); your view needs it to verify every Delivery.
`webhook_subscriptions.list()`, `retrieve()`, `update()` and `delete()`
manage the subscription from then on. `update()` requires `if_match`, as
[Safe updates with ETags](etags.md) explains.

## Verify a Delivery in your web app

`Webhook.construct_event()` checks a Delivery and returns its Event, or a
`TestDelivery` (from `teachmehipaa.types`, like every model). Hand it these,
untouched:

1. **The raw body, as bytes.** JSON that something parsed and serialized
   again never verifies, so read the body before any middleware does.
2. **The headers.** A plain dict works, and so do the `request.headers` of
   Flask, Starlette and Django.
3. **The path the Delivery was sent to, with its query string**, or the
   full URL. The signature covers it, so a view that passes the path
   without its query string rejects every Delivery.

The fourth argument is the Signing secret. `construct_event` rejects a
Delivery signed more than 300 seconds before or after your clock time;
`tolerance=` changes that window. A failed check raises
`WebhookSignatureError`, whose `code` names the check: `missing_header`,
`invalid_timestamp`, `timestamp_outside_tolerance`, `body_hash_mismatch` or
`signature_mismatch`. Answer it with a 400.

An Event type this version of the library doesn't know comes back as
`UnknownEvent`, so a new type can't crash your view. TeachMeHIPAA may
deliver one Event more than once; key your side effects on `event.event_id`.

`Webhook` needs a Signing secret and nothing else, so a web worker can
verify Deliveries without building an API client. Each client also exposes
it as `client.webhooks`.

### Flask

Read the body with `request.get_data()`. Flask's `request.full_path` ends in
`?` even when there is no query string, so strip it:

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

In FastAPI or Starlette, `await request.body()` gives you the bytes, and
`str(request.url)` keeps the query string and any mount prefix:

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

`construct_event` is plain CPU work (an HMAC and a hash), so calling it from
an `async def` view doesn't block the event loop on I/O.

### Django

Use `request.body` and `request.get_full_path()`, and exempt the view from
CSRF, because the signature already authenticates the request:

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
the path from the subscription's `endpoint_url` (the one TeachMeHIPAA
signed) instead of the one your framework reports.

## Send yourself a Test delivery

`webhook_subscriptions.test()` sends a signed Test delivery to the
subscription's endpoint, so you can check your view end to end. It carries
no Event: `construct_event` returns a `TestDelivery` holding the
`subscription_id`, and your view should answer it with 2xx, as the views
above do.

The call returns an Operation that finishes once your endpoint has
answered. Wait for it and read the outcome from `response`:

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

`webhook_subscriptions.redrive()` sends a subscription's failed Deliveries
again and returns the same kind of Operation. A result's `tag` is `sent`,
`failed` or `settled` (that Delivery had already finished). More tags may
appear later, so keep a fallback branch; they parse as
`UnknownWebhookDeliveryResult`.

## Sign Deliveries in your own tests

`Webhook.generate_test_headers()` signs a payload the way TeachMeHIPAA does.
Give it the body, a Signing secret and the path, and send the headers it
returns along with that body:

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

[Testing](testing.md#test-your-webhook-view) runs this inside a pytest test
of a Flask view.
