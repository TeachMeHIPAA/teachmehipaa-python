# TeachMeHIPAA Python Library

The official Python library for the
[TeachMeHIPAA Developer API](https://api.tme.so/v1). It handles Access tokens,
the Organization binding, retries, idempotency keys, typed errors, pagination,
ETags, Operations and webhook verification, so your code only calls methods.
It has a synchronous client and an asyncio client with the same methods.

> [!NOTE]
> The Developer API has not launched yet, and this package is not on PyPI.
> Until it is, install it from a local checkout.

## Contents

- [Installation](#installation)
- [Quickstart](#quickstart)
- [The Organization binding](#the-organization-binding)
- [Public lookups without credentials](#public-lookups-without-credentials)
- [Creating Learners](#creating-learners)
- [Pagination](#pagination)
- [Errors](#errors)
- [Retries and idempotency](#retries-and-idempotency)
- [Conditional writes and reads](#conditional-writes-and-reads)
- [Operations](#operations)
- [Uploads and downloads](#uploads-and-downloads)
- [Webhooks](#webhooks)
- [Partner apps](#partner-apps)
- [Tailing the Event log](#tailing-the-event-log)
- [Async usage](#async-usage)
- [Configuration](#configuration)
- [Logging](#logging)
- [Versioning](#versioning)
- [Support and security](#support-and-security)

## Installation

```sh
pip install teachmehipaa
# or
uv add teachmehipaa
```

Python 3.10 or newer. The library depends on `httpx` and `pydantic` 2, and
ships type hints (`py.typed`).

## Quickstart

Create an API client in the TeachMeHIPAA console to get a client id
(`cli_…`) and secret (`tmh_cs_…`). Start in the Sandbox Environment, where no
real Learners are emailed and no real money moves.

<!-- sample: quickstart -->
```python
import os

from teachmehipaa import TeachMeHipaa

client = TeachMeHipaa(
    client_id=os.environ["TMH_CLIENT_ID"],
    client_secret=os.environ["TMH_CLIENT_SECRET"],
    environment="sandbox",
)

learner = client.learners.retrieve("sub_01JD80AB2C3D4E5F6G7H8J9K0M")
print(learner.name, learner.status)

for item in client.learners.list(status="in_progress", limit=20):
    print(item.email)
```

The client exchanges your credentials for an Access token on the first call,
caches it and renews it 60 seconds before it expires. Concurrent calls share
one token request. If the API rejects a token mid-flight (401), the client
renews it once and replays the call; that replay doesn't count as a retry.

Methods take keyword arguments, except ids in the path, which come first and
positionally: `client.learners.retrieve(learner_id, course_id=...)`. Every
object they return has a `last_response` with the HTTP `status`, `headers`,
`request_id` and `etag`.

The client holds an `httpx` connection pool. Call `client.close()` when you
are done with it, or use it as a context manager: `with TeachMeHipaa(...) as
client:`. To ask for fewer Scopes than your API client holds, pass
`scopes=["learners:read"]`.

## The Organization binding

An API client belongs to one Organization, so you never pass an `org_id`. On
the first Organization-scoped call, the client asks `auth.introspect` which
Organization the token is for, once, and remembers the answer. If you already
know the id, pass it and the client skips that lookup:

<!-- sample: organization -->
```python
import os

from teachmehipaa import TeachMeHipaa

client = TeachMeHipaa(
    client_id=os.environ["TMH_CLIENT_ID"],
    client_secret=os.environ["TMH_CLIENT_SECRET"],
    organization_id="org_acme",
)

compliance = client.compliance.retrieve()
print(compliance.compliant_rate, compliance.last_response.request_id)
```

A client's configuration is fixed when you create it. To act for another
Organization, create another client. Partner-level calls (`partners.*`) are
not Organization-scoped and take the `partner_id` as their first argument.

## Public lookups without credentials

Public methods, `courses.list`, `courses.retrieve` and
`certificate_verifications.retrieve`, send no Access token at all. To call
only those, such as to check a Certificate someone showed you, create a
client without credentials:

<!-- sample: public-lookups -->
```python
from teachmehipaa import TeachMeHipaa

client = TeachMeHipaa(environment="sandbox")

verification = client.certificate_verifications.retrieve("aB3dE9")
print(verification.status, verification.learner_name)

for course in client.courses.list():
    print(course.title)
```

Any other method on such a client raises `ValueError` before it sends
anything. Pass `client_id` and `client_secret`, or a `token_provider`, to
call them. `AsyncTeachMeHipaa(environment="sandbox")` works the same way.

## Creating Learners

`create` and `upsert_by_external_id` say whether they created the Learner in
`created`. `upsert_by_external_id` is safe to replay from a sync job: it
creates and invites the Learner the first time and returns them every time
after.

<!-- sample: learner-writes -->
```python
created = client.learners.create(
    email="ana@example.com",
    name="Ana Example",
    course_id="hipaa-2026",
)
print("invited" if created.created else "already enrolled")

synced = client.learners.upsert_by_external_id(
    "hr-123", email="ana@example.com", name="Ana Example"
)
print(synced.learner_id)
```

Samples from here on assume a `client` created as in the
[Quickstart](#quickstart).

## Pagination

A list method returns one page, with `items` and `next_cursor`. Iterating the
page yields every item across all pages, fetching the next page only when the
loop reaches it, and stops fetching when you `break`.

<!-- sample: pagination -->
```python
# Every Learner, page by page, fetched lazily.
for learner in client.learners.list(limit=100):
    print(learner.learner_id)

# One page at a time.
page = client.enrollments.list(limit=50)
print(len(page.items))
while page.has_next_page():
    page = page.get_next_page()
    print(len(page.items))
```

`page.iter_pages()` yields each page in turn, and `auto_paging_iter()` is an
alias for iterating the page, as in Stripe's library.

## Errors

Failed calls raise a subclass of `TeachMeHipaaError`, chosen by HTTP status:

| Class                     | When                                                     |
| ------------------------- | -------------------------------------------------------- |
| `InvalidRequestError`     | 400, 405, 406, 415 and 422                               |
| `IdempotencyError`        | 422 `idempotency_key_reuse` (an `InvalidRequestError`)   |
| `AuthenticationError`     | 401                                                      |
| `PermissionDeniedError`   | 403, such as a missing Scope                             |
| `NotFoundError`           | 404                                                      |
| `ConflictError`           | 409                                                      |
| `PreconditionFailedError` | 412 (stale ETag) and 428 (missing `if_match`)            |
| `RateLimitError`          | 429, with `retry_after` in seconds                       |
| `APIError`                | 5xx, or a response that isn't JSON (such as an HTML page) |
| `APIConnectionError`      | No response arrived                                      |
| `APITimeoutError`         | No response within `timeout` (an `APIConnectionError`)   |
| `OAuthError`              | The token endpoint refused to issue a token              |

The names follow PEP 8 (`APIError`, not `ApiError`). Each error carries the
problem's `code` (branch on it; new codes can appear at any time), `title`,
`detail`, field-level `errors`, the `status`, the response `headers` and the
`request_id` to quote to support.

<!-- sample: errors -->
```python
from teachmehipaa import NotFoundError, PermissionDeniedError, TeachMeHipaaError

try:
    client.learners.retrieve("sub_01JD80AB2C3D4E5F6G7H8J9K0M")
except NotFoundError:
    print("No such Learner")
except PermissionDeniedError as error:
    print("Missing a Scope:", error.detail)
except TeachMeHipaaError as error:
    print(error.code, error.detail, error.request_id)
    for field in error.errors:
        print(field.path, field.message)
```

## Retries and idempotency

The client retries network errors, 409 `conflict`, 429 and 5xx up to
`max_retries` times (2 by default), backing off from 0.5 s up to 5 s with
jitter and honoring `Retry-After` up to 60 s. It only retries calls that are
safe to replay: reads, writes that carry an `Idempotency-Key`, and the few
writes that are idempotent by nature, such as `seat_orders.quote`. PATCH and
DELETE are never retried, and take no key: the API ignores one on them.

Every create and custom method gets a generated UUID `Idempotency-Key`,
reused by each of its retries, so a retry never enrolls a Learner twice or
charges twice. Pass your own to make a call safe to repeat across processes.
`max_retries` and `timeout` (in seconds) override the client's settings for
one call, and `request_id` sends your own `x-request-id` on every attempt so
the call can be found in your logs and TeachMeHIPAA's. The API echoes an id
that matches `^[A-Za-z0-9._-]{1,128}$` and replaces any other:

<!-- sample: request-options -->
```python
enrollment = client.enrollments.create(
    email="ana@example.com",
    course_id="hipaa-2026",
    idempotency_key="hr-sync-2026-11-15-ana",
    max_retries=5,
    timeout=10.0,
    request_id="hr-sync-2026-11-15-ana",
)
print(enrollment.enrollment_id, enrollment.last_response.request_id)
```

## Conditional writes and reads

Updates that the API guards with ETags take `if_match`: the ETag string, or
the object you read, whose `last_response.etag` the client sends.
`learners.update` and `webhook_subscriptions.update` require it, since the
API refuses them without one; on `learners.offboard` it is optional. A stale
ETag raises `PreconditionFailedError`.

Updates are merge patches. An argument you leave out (or pass as
`NOT_GIVEN`) is not sent and stays unchanged; `None` is sent as JSON `null`
and clears the field.

<!-- sample: conditional-write -->
```python
from teachmehipaa import PreconditionFailedError

learner = client.learners.retrieve("sub_01JD80AB2C3D4E5F6G7H8J9K0M")
try:
    updated = client.learners.update(
        learner.learner_id,
        if_match=learner,
        name="Ana Q. Example",
        external_id=None,
    )
    print(updated.name)
except PreconditionFailedError:
    print("Someone else changed this Learner; read it again")
```

A retrieve that takes `if_none_match` returns `NotModified` when your copy is
still current (304). `NotModified` is falsy, so `or` picks your copy:

<!-- sample: not-modified -->
```python
from teachmehipaa import NotModified

course = client.courses.retrieve("hipaa-2026")

latest = client.courses.retrieve("hipaa-2026", if_none_match=course)
if isinstance(latest, NotModified):
    print("still current")
course = latest or course
print(course.title)
```

## Operations

Exports, imports, batch writes, Test deliveries and redrives return an
`Operation`. `wait()` polls until it is done (backing off from `interval`,
default 1 s, to 10 s) and raises `OperationTimeoutError` after `timeout`
(default 300 s), or `OperationFailedError` if it finished with an error; both
carry the `operation`. An Operation that is already done, as exports always
are, returns without a request. An export's `export_result()` hands back the
CSV.

<!-- sample: operations -->
```python
operation = client.learners.export(format="csv", course_id="hipaa-2026")
done = operation.wait(timeout=60, interval=2)
export = done.export_result()
print(export.filename, export.row_count, len(export.csv))
```

`operation_id_from_name(operation.name)` gives the id that
`operations.retrieve` takes, if you want to check on an Operation later.

## Uploads and downloads

An Enrollment import takes the CSV as a path (`str` or `pathlib.Path`),
`bytes`, or a file opened with `"rb"`. A `str` is always a path; pass CSV text
as `text.encode()`. The file is read once per call, so a retry resends the
same bytes.

Certificate PDFs come back whole as a `BinaryResponse` (`content`,
`content_type`, `filename`). Pass `stream=True` to read one as it arrives,
the way `httpx` streams; close the stream, ideally with `with`.

<!-- sample: files -->
```python
from pathlib import Path

preview = client.enrollments.preview_import(
    file=Path("roster.csv"), options={"course_id": "hipaa-2026"}
)
print(preview.valid_rows, "of", preview.total_rows, "rows are valid")
client.enrollments.import_(file="roster.csv").wait()

pdf = client.certificates.download_pdf("cert_01JD8F")
Path(pdf.filename or "certificate.pdf").write_bytes(pdf.content)

with (
    client.certificates.download_pdf("cert_01JD8F", stream=True) as stream,
    open("certificate-copy.pdf", "wb") as out,
):
    for chunk in stream.iter_bytes():
        out.write(chunk)
```

On the async client, `async with await client.certificates.download_pdf(...,
stream=True) as stream:` and `async for chunk in stream.aiter_bytes():`.

## Webhooks

`Webhook.construct_event` verifies a Delivery and returns its Event, or a
`TestDelivery` (from `teachmehipaa.types`, like every model). It needs three things exactly as they arrived:

1. **The raw body.** Parsed and re-serialized JSON never verifies, so read
   the body as bytes before anything parses it.
2. **The headers.** A dict works, and so do Flask's, Starlette's and
   Django's `request.headers`.
3. **The request path, with its query string, or the full URL.** The
   signature covers the path the Delivery was sent to, so a verifier that
   drops the path, or its query string, rejects every Delivery.

Deliveries signed more than 5 minutes from your clock, in either direction,
are rejected. Verification raises `WebhookSignatureError` with a `code` such
as `signature_mismatch`; answer it with 400. Event types this version doesn't
know arrive as an `UnknownEvent`, so new types never break your handler.

`Webhook` needs only the Signing secret, never API credentials, so a handler
can import it without creating a client. It is also on the clients as
`TeachMeHipaa.webhooks`.

With **Flask**, read the body with `request.get_data()`. `request.full_path`
always ends in `?`, even with no query string, so strip it:

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

With **FastAPI** (or Starlette), read `await request.body()` and pass the
full `request.url`, which keeps any mount path and the query string:

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

With **Django**, use `request.body` and `request.get_full_path()`, and exempt
the view from CSRF checks, since the signature authenticates the request:

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

To test your handler, sign a payload the way TeachMeHIPAA does with
`Webhook.generate_test_headers`:

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

## Partner apps

A Partner app acts for many Organizations, each connected through a Grant
that an admin approves on the TeachMeHIPAA consent screen. `oauth` builds
the consent URL with a PKCE challenge and exchanges the returned code. Keep
the `state` and `code_verifier` in the admin's server-side session between
the two steps. The `sessions` and `grants` objects below stand in for your
own storage.

<!-- sample: partner-consent -->
```python
import os

from teachmehipaa import oauth

REDIRECT_URI = "https://partner.example.com/tmh/callback"


def start_consent() -> str:
    """Returns the URL to send the Organization's admin to."""
    pkce = oauth.create_pkce_pair()
    state = oauth.create_state()
    sessions.save(state=state, code_verifier=pkce.code_verifier)
    return oauth.authorize_url(
        client_id=os.environ["TMH_APP_ID"],
        redirect_uri=REDIRECT_URI,
        scopes=["learners:read", "learners:write"],
        state=state,
        code_challenge=pkce.code_challenge,
    )


def finish_consent(code: str, state: str) -> None:
    """Handles the redirect back to REDIRECT_URI."""
    saved = sessions.load()
    if state != saved.state:
        raise PermissionError("state mismatch: possible CSRF")
    grant = oauth.exchange_code(
        client_id=os.environ["TMH_APP_ID"],
        client_secret=os.environ["TMH_APP_SECRET"],
        code=code,
        redirect_uri=REDIRECT_URI,
        code_verifier=saved.code_verifier,
    )
    grants.save("org_acme", grant.refresh_token)
```

A code works once, within 10 minutes, so the exchange is never retried.

Then create a client per authorized Organization with a
`PartnerGrantTokenProvider` and a token store: any object with `load()` and
`save(refresh_token)`. Every token exchange rotates the Grant's Refresh
token, and the provider saves each new one to the store before it uses the
Access token that came with it.

<!-- sample: partner-grant -->
```python
import os

from teachmehipaa import PartnerGrantTokenProvider, TeachMeHipaa


class GrantStore:
    """The Refresh token of one Organization's Grant."""

    def __init__(self, org_id: str) -> None:
        self.org_id = org_id

    def load(self) -> str:
        return grants.load(self.org_id)

    def save(self, refresh_token: str) -> None:
        grants.save(self.org_id, refresh_token)


client = TeachMeHipaa(
    token_provider=PartnerGrantTokenProvider(
        client_id=os.environ["TMH_APP_ID"],
        client_secret=os.environ["TMH_APP_SECRET"],
        token_store=GrantStore("org_acme"),
    ),
    organization_id="org_acme",
)

print(len(client.learners.list().items))
```

> [!WARNING]
> Presenting a superseded Refresh token revokes the whole Grant (ADR-0004).
> So `save` must persist durably before it returns, you should create one
> provider per Grant and share it between clients, and a Refresh token
> exchange is **never retried**: a network error during one raises
> `APIConnectionError`, and an `OAuthError` with code `invalid_grant` means
> the Organization must go through consent again. Never retry these yourself
> with an old Refresh token. If `save` raises, the client raises
> `TokenStoreError` and doesn't use the new token.

Give the provider the same `environment` (and `base_url`) as the client:
a client refuses, with `ValueError`, a provider that would exchange Refresh
tokens against another Environment.

The asyncio versions are `AsyncPartnerGrantTokenProvider` (with an
`AsyncTokenStore`, whose methods are `async`) and `oauth.async_exchange_code`.

For the Partner's own calls, such as listing and creating customer
Organizations, authenticate with the Partner app's own id (`app_…`) and
secret (`tmh_as_…`) as `client_id` and `client_secret`, and pass your
`partner_id`:

<!-- sample: partner-organizations -->
```python
import os

from teachmehipaa import TeachMeHipaa

partner = TeachMeHipaa(
    client_id=os.environ["TMH_APP_ID"],
    client_secret=os.environ["TMH_APP_SECRET"],
)

for organization in partner.partners.organizations.list(
    "ptn_01JD8E2C3D4E5F6G7H8J9K0M1N"
):
    print(organization.org_id, organization.grant_active)
```

If you get Access tokens some other way, pass
`token_provider=StaticTokenProvider(access_token)` (or
`AsyncStaticTokenProvider` on the async client). A static token is never
renewed; once it expires, calls raise `AuthenticationError`.

## Tailing the Event log

`events.tail` reads the Event log oldest first and keeps its own position in
`last_event_id`. Save it, and resume from it after a restart to catch up on
anything you missed while down, without webhooks. Here `cursors` stands in
for your own storage and `shutdown` is a `threading.Event` your service sets
when it stops:

<!-- sample: events-tail -->
```python
tail = client.events.tail(after=cursors.load(), follow=True, interval=5, stop=shutdown)
for event in tail:
    print(event.event_type, event.event_id)
    cursors.save(tail.last_event_id)
```

Without `follow`, the loop ends once it has caught up. With it, the tail
polls every `interval` seconds until you `break` or set `stop`. On the async
client, iterate with `async for` (no `await` before `tail`) and pass an
`asyncio.Event` as `stop`.

## Async usage

`AsyncTeachMeHipaa` takes the same options and has the same methods; await
each call. Await a list call for its first page, then `async for` over it to
get every item:

<!-- sample: async -->
```python
import asyncio
import os

from teachmehipaa import AsyncTeachMeHipaa


async def main() -> None:
    async with AsyncTeachMeHipaa(
        client_id=os.environ["TMH_CLIENT_ID"],
        client_secret=os.environ["TMH_CLIENT_SECRET"],
        environment="sandbox",
    ) as client:
        learner, compliance = await asyncio.gather(
            client.learners.retrieve("sub_01JD80AB2C3D4E5F6G7H8J9K0M"),
            client.compliance.retrieve(),
        )
        print(learner.name, compliance.compliant_rate)

        async for item in await client.learners.list(limit=100):
            print(item.email)


asyncio.run(main())
```

Concurrent calls share one token request and one Organization lookup.
Cancelling a task cancels its request, its retries and any `wait()`.

## Configuration

<!-- sample: configuration -->
```python
import os

import httpx

from teachmehipaa import TeachMeHipaa

client = TeachMeHipaa(
    client_id=os.environ["TMH_CLIENT_ID"],
    client_secret=os.environ["TMH_CLIENT_SECRET"],
    environment="sandbox",
    scopes=["learners:read", "learners:write"],
    organization_id="org_acme",
    max_retries=3,
    timeout=30.0,
    app_info={
        "name": "acme-hr-sync",
        "version": "4.2.0",
        "url": "https://acme.example",
    },
    http_client=httpx.Client(timeout=30.0),
)
print(client.environment, client.base_url, client.max_retries)
```

Every option is keyword-only:

| Option            | Default                               | Description                                                                          |
| ----------------- | ------------------------------------- | ------------------------------------------------------------------------------------ |
| `client_id`       | None: public methods only             | Your API client's id (`cli_…`), or a Partner app's (`app_…`)                         |
| `client_secret`   | Required with `client_id`             | The matching secret (`tmh_cs_…` or `tmh_as_…`)                                       |
| `scopes`          | Every Scope the API client holds      | Narrows the Access token's Scopes                                                    |
| `token_provider`  | Client credentials                    | Supplies Access tokens instead: `PartnerGrantTokenProvider`, `StaticTokenProvider`   |
| `environment`     | `"live"`                              | `"live"` or `"sandbox"`; credentials work only in their own Environment              |
| `base_url`        | The Environment's URL                 | Overrides it, e.g. to point at a mock server                                         |
| `organization_id` | Looked up once with `auth.introspect` | The Organization to act for                                                          |
| `max_retries`     | `2`                                   | Retries of a failed call that is safe to replay                                      |
| `timeout`         | `80.0`                                | Seconds to wait for each response; a float or an `httpx.Timeout`                     |
| `app_info`        | None                                  | `{"name": ..., "version": ..., "url": ...}` of your software, sent in the User-Agent |
| `http_client`     | A new `httpx.Client` (`AsyncClient`)  | Sends requests, e.g. with a proxy, mTLS or a mock transport; closed by `close()`     |
| `clock`, `sleep`  | `time.monotonic`, `time.sleep`        | Supply the time and waits, for tests (`asyncio.sleep` on the async client)           |

Pass either `client_id` and `client_secret`, or `token_provider`, not both;
`scopes` then belong to the token provider. With neither, the client makes
only public calls. Base URLs: Live is
`https://api.tme.so/v1`; Sandbox is `https://api-teachmehipaa-dev.web.app/v1`.
`environment`, `base_url`, `max_retries` and `timeout` can be read back from
the client.

## Logging

The library prints nothing, sends no telemetry and writes nothing to disk.
It logs through the standard `logging` module, to the logger named
`teachmehipaa`: one DEBUG record per HTTP response, token requests included,
with the method, the path (without its query string, which can hold Learner
emails), the status, the latency and the request id. Request and response
bodies, headers and credentials are never logged (ADR-0007), because they
hold Learner details. Nothing appears until you turn DEBUG on for the logger:

<!-- sample: logging -->
```python
import logging

logging.basicConfig()
logging.getLogger("teachmehipaa").setLevel(logging.DEBUG)

client.learners.list()
# DEBUG:teachmehipaa:GET /v1/organizations/org_acme/learners 200 in 84 ms (request id req_7f3c2a)
```

Each record also carries the fields as attributes (`method`, `path`,
`status`, `latency_ms`, `request_id`) for structured log handlers.

## Versioning

The library follows semantic versioning. Its resources and models are
generated from the Developer API's OpenAPI document; `OPENAPI_VERSION` in
this repository names the document release this version was generated from.
Models are tolerant: unknown response fields are kept, and enum fields accept
values this version doesn't know, so API additions don't break your code. See
the [changelog](CHANGELOG.md).

## Support and security

<!-- TODO(Nick): confirm the support address before launch. -->

For help, contact TeachMeHIPAA support and quote the `request_id` from the
error or `last_response`. To report a vulnerability, see
[SECURITY.md](SECURITY.md); please don't open a public issue.

See [CONTRIBUTING.md](CONTRIBUTING.md) to work on the library.
