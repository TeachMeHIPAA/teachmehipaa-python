# Testing

Test your integration in three layers: unit tests against a fake transport
that never leave your process, webhook handler tests with Deliveries you
sign yourself, and end-to-end runs against the Sandbox.

## Unit tests with a fake transport

The client sends every request through an `httpx` client, so a test can
pass one whose transport answers from your own code. `httpx.MockTransport`
takes a function from request to response. Give the client a static token
and an `organization_id` so it makes no token or Organization lookup
requests, and `max_retries=0` so a failure shows up at once:

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

Responses use the API's JSON field names (camelCase), as in the
[OpenAPI document](../../openapi/openapi.developer.json); the models turn
them into snake_case attributes. Errors are Problem Details with a `code`,
so the 404 above raises `NotFoundError` with `code == "not_found"`. On the
async client, pass `httpx.AsyncClient(transport=httpx.MockTransport(...))`;
the handler can be a plain or an `async` function.

To test retries and `wait()` without waiting, pass `sleep` (and `clock`)
functions to the client: they replace `time.sleep` and `time.monotonic`
(`asyncio.sleep` on the async client). See
[Configuration](configuration.md).

## Test your webhook handler

`Webhook.generate_test_headers` signs a body the way TeachMeHIPAA signs a
Delivery, so a test can post a Delivery to your handler through your
framework's test client. Use a test Signing secret, and sign for the path
the test posts to:

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
`timestamp`. [Webhooks](webhooks.md) has handlers for FastAPI and Django.

## End-to-end tests in the Sandbox

The Sandbox runs the real API against separate data and separate
credentials, and only emails allowlisted addresses, so you can create
Learners and Enrollments there freely. Point a client at it with
`environment="sandbox"` and Sandbox credentials. To check a webhook
endpoint you've deployed, run `webhook_subscriptions.test` against it (see
[Test deliveries](webhooks.md#test-deliveries)).

Keep Sandbox tests out of your default test run, since they need
credentials and the network. A pytest marker does that:

```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = ["-m", "not sandbox"]
markers = ["sandbox: calls the TeachMeHIPAA Sandbox"]
```

Then run them with `pytest -m sandbox`, with `TMH_CLIENT_ID` and
`TMH_CLIENT_SECRET` set to Sandbox credentials.
