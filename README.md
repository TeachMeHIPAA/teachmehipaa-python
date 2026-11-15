# teachmehipaa

The official Python library for the TeachMeHIPAA Developer API.

> Pre-release. Nothing is published to PyPI yet.

```python
from teachmehipaa import TeachMeHipaa

with TeachMeHipaa(
    client_id="cli_...",
    client_secret="tmh_cs_...",
    environment="sandbox",
) as client:
    learner = client.learners.retrieve("sub_...")
    print(learner.status, learner.last_response.request_id)
```

`AsyncTeachMeHipaa` has the same surface with `await`.

## Partner apps

Send the Organization admin to the consent URL, then exchange the code from
the redirect once. Keep the code verifier and state server-side.

```python
from teachmehipaa import PartnerGrantTokenProvider, TeachMeHipaa, oauth

pkce = oauth.create_pkce_pair()
state = oauth.create_state()
url = oauth.authorize_url(
    client_id="app_...",
    redirect_uri="https://example.com/oauth/callback",
    scopes=["learners:read", "learners:write"],
    state=state,
    code_challenge=pkce.code_challenge,
)

# On the redirect, after checking its state matches:
grant = oauth.exchange_code(
    client_id="app_...",
    client_secret="tmh_as_...",
    code=code,
    redirect_uri="https://example.com/oauth/callback",
    code_verifier=pkce.code_verifier,
)
store.save(grant.refresh_token)
```

A Grant's client takes a token provider and your token store, an object with
`load()` and `save(refresh_token)`. Every exchange rotates the Refresh token,
and presenting a superseded one revokes the Grant, so the provider saves each
new one before it uses the Access token and never retries an exchange. Create
one provider per Grant and share it.

```python
client = TeachMeHipaa(
    token_provider=PartnerGrantTokenProvider(
        client_id="app_...", client_secret="tmh_as_...", token_store=store
    ),
)
```

`StaticTokenProvider("eyJ...")` sends an Access token you got yourself.

## Pagination

A list method returns one page (`.items`, `.next_cursor`). Iterating the page
fetches the pages after it lazily, until `next_cursor` is `None`, and stops
fetching when you break out of the loop:

```python
for learner in client.learners.list(status="in_progress", limit=100):
    print(learner.email)
```

With `AsyncTeachMeHipaa`, await the call for the first page and `async for`
over it, as in Stripe's library:

```python
async for learner in await client.learners.list():
    print(learner.email)
```

`page.has_next_page()`, `page.get_next_page()` and `page.iter_pages()` work a
page at a time; `auto_paging_iter()` is an alias for iterating.

`client.events.tail(after=last_event_id)` yields only Events newer than
`after` and keeps its position in `tail.last_event_id`; save it to resume
after a restart. With `follow=True` it polls every `interval` seconds
(default 2) until you break or set `stop` (a `threading.Event`, or an
`asyncio.Event` on the async client, where the tail is iterated with
`async for` and no `await`).

## ETags and merge patches

Every returned object has `last_response.etag`. Pass it, or the object
itself, as `if_match=`; a stale ETag raises `PreconditionFailedError`:

```python
learner = client.learners.retrieve("sub_...")
client.learners.update("sub_...", if_match=learner, external_id=None)
```

Updates are merge patches: an argument you leave out (or pass `NOT_GIVEN`)
is not sent and stays unchanged; `None` is sent as JSON `null` and clears the
field.

A retrieve that supports `if_none_match=` returns `NotModified` when your copy
is still current. `NotModified` is falsy:

```python
course = client.courses.retrieve("hipaa-2026", if_none_match=cached) or cached
```

## Certificate PDFs

`download_pdf` reads the whole file into a `BinaryResponse` (`.content`,
`.content_type`, `.filename`). Pass `stream=True` to read it as it arrives,
the way httpx streams; close the stream, ideally with `with`:

```python
with client.certificates.download_pdf("cert_...", stream=True) as pdf:
    for chunk in pdf.iter_bytes():
        out.write(chunk)
```

On the async client: `async with await client.certificates.download_pdf(...,
stream=True) as pdf:` and `async for chunk in pdf.aiter_bytes()`.

## CSV imports

`enrollments.preview_import(file=...)` and `enrollments.import_(file=...)` take
a path (`str` or `pathlib.Path`), `bytes`, or a file opened with `"rb"`. The
file is read once per call, so a retry resends the same bytes. A `str` is
always a path; pass CSV text as `text.encode()`.

## Operations

Exports, bulk writes, Test deliveries and redrives return an `Operation`.
`wait()` polls until it is done (backing off from `interval`, default 1 s,
to 10 s) and raises `OperationTimeoutError` after `timeout` (default 300 s)
or `OperationFailedError` if it finished with an error. An Operation that is
already done, as exports always are, returns without a request:

```python
export = client.enrollments.export(format="csv").wait()
print(export.export_result().csv)

delivery = client.webhook_subscriptions.test("whs_...").wait(timeout=60)
print(delivery.response.tag)  # "sent", "failed" or "settled"
```

On `AsyncTeachMeHipaa`, `await operation.wait()`; cancelling the task stops
it. `operation_id_from_name(operation.name)` gives the id that
`operations.retrieve` takes.
