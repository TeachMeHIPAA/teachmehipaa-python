# Testing

Three layers cover an integration: unit tests that answer from a fake
transport and never leave the process, tests of your webhook view with
Deliveries you sign yourself, and a few end-to-end runs against the
Sandbox. The examples use pytest, but nothing here depends on it.

## Unit-test with `httpx.MockTransport`

The client sends every request through an `httpx` client, so a test can
give it one whose transport is a plain function from request to response.
Use a static token and an `organization_id` so the client skips the token
and Organization requests, and `max_retries=0` so a failure fails at once:

<!-- sample: fake-transport -->
```python
import httpx

from teachmehipaa import StaticTokenProvider, TeachMeHipaa

COMPLIANCE = {
    "asOf": "2026-11-15T12:00:00.000Z",
    "courseId": "hipaa-2026",
    "totals": {
        "learners": 4,
        "compliant": 3,
        "expiringSoon": 1,
        "expired": 0,
        "inProgress": 1,
        "notStarted": 0,
        "inviteBounced": 0,
    },
    "compliantRate": 0.75,
}


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/v1/organizations/org_test/compliance":
        return httpx.Response(200, json=COMPLIANCE)
    return httpx.Response(
        404, json={"title": "Not found", "status": 404, "code": "not_found"}
    )


client = TeachMeHipaa(
    token_provider=StaticTokenProvider("test-token"),
    organization_id="org_test",
    http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    max_retries=0,
)
print(client.compliance.retrieve().compliant_rate)
```

Write responses with the API's JSON field names (camelCase), as in the
[OpenAPI document](../../openapi/openapi.developer.json); the models map
them to snake_case attributes. Errors are Problem Details with a `code`, so
the 404 above raises `NotFoundError` with `code == "not_found"`. For
`AsyncTeachMeHipaa`, pass
`httpx.AsyncClient(transport=httpx.MockTransport(handler))`; the handler can
be a plain function or a coroutine function.

Retries and `wait()` sleep between attempts. To keep tests fast, pass the
client your own `sleep` (and `clock`) in place of `time.sleep` and
`time.monotonic` (`asyncio.sleep` on the async client).
[Advanced usage](advanced-usage.md#every-client-option) lists both.

## Test your webhook view

`Webhook.generate_test_headers()` signs a body the way TeachMeHIPAA signs a
Delivery, so a test can post a Delivery through your framework's test
client. Use a test Signing secret and sign for the path you post to:

<!-- sample: webhook-handler-test -->
```python
import json

from flask import Flask, request

from teachmehipaa import Webhook, WebhookSignatureError

SIGNING_SECRET = "test-signing-secret"
app = Flask(__name__)


@app.post("/webhooks/tmh")
def tmh_webhook() -> tuple[str, int]:
    try:
        Webhook.construct_event(
            request.get_data(), request.headers, SIGNING_SECRET, request.path
        )
    except WebhookSignatureError as error:
        return error.code, 400
    return "ok", 200


def test_accepts_a_signed_test_delivery() -> None:
    body = json.dumps({"subscriptionId": "whs_test", "test": True})
    headers = Webhook.generate_test_headers(body, SIGNING_SECRET, "/webhooks/tmh")

    response = app.test_client().post("/webhooks/tmh", data=body, headers=headers)

    assert response.status_code == 200


def test_rejects_a_changed_body() -> None:
    body = json.dumps({"subscriptionId": "whs_test", "test": True})
    headers = Webhook.generate_test_headers(body, SIGNING_SECRET, "/webhooks/tmh")

    response = app.test_client().post(
        "/webhooks/tmh", data=body.replace("true", "false"), headers=headers
    )

    assert response.status_code == 400
```

`generate_test_headers` signs with the current time unless you pass
`timestamp=`, which is how you test the 300-second tolerance.
[Webhooks](webhooks.md) has the matching views for FastAPI and Django.

## Run end-to-end tests in the Sandbox

The Sandbox runs the real API on separate data, with separate credentials,
and emails only allowlisted addresses, so a test can create Learners and
Enrollments freely. Build the client with `environment="sandbox"` and
Sandbox credentials. To check a deployed webhook endpoint, call
`webhook_subscriptions.test()` against it (see
[Send yourself a Test delivery](webhooks.md#send-yourself-a-test-delivery)).

These tests need credentials and the network, so keep them out of the
default run with a pytest marker:

```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = ["-m", "not sandbox"]
markers = ["sandbox: calls the TeachMeHIPAA Sandbox"]
```

Run them with `pytest -m sandbox`, with `TMH_CLIENT_ID` and
`TMH_CLIENT_SECRET` set to Sandbox credentials.
