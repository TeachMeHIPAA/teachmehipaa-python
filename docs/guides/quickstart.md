# Quickstart

You need Python 3.10 or newer. The package pulls in `httpx`, `pydantic` 2
and `typing-extensions`, and ships inline type hints (`py.typed`), so mypy
and Pyright check your calls with no stub package.

## Install it

> [!NOTE]
> `teachmehipaa` isn't on PyPI yet. The Developer API is still in
> pre-release, so install the package straight from GitHub, and expect
> names to move before 1.0.0.

```sh
pip install "teachmehipaa @ git+https://github.com/TeachMeHIPAA/teachmehipaa-python"
```

With uv, `uv add "teachmehipaa @ git+https://github.com/TeachMeHIPAA/teachmehipaa-python"`
does the same and pins the commit in `uv.lock`.

## Get Sandbox credentials

An Organization admin creates an API client in the TeachMeHIPAA console.
You get a client id (`cli_…`) and a secret (`tmh_cs_…`). Each API client
belongs to one Organization and one Environment. Build against the
**Sandbox** Environment: it never emails real Learners, and its credentials
can't touch Live data.

Keep the secret in the environment, where every sample here reads it:

```sh
export TMH_CLIENT_ID=cli_...
export TMH_CLIENT_SECRET=tmh_cs_...
```

## Make a request

<!-- sample: first-call -->
```python
import os

from teachmehipaa import TeachMeHipaa

with TeachMeHipaa(
    client_id=os.environ["TMH_CLIENT_ID"],
    client_secret=os.environ["TMH_CLIENT_SECRET"],
    environment="sandbox",
) as client:
    compliance = client.compliance.retrieve()
    print(f"{compliance.compliant_rate:.0%} of Learners are compliant")

    for learner in client.learners.list(limit=20):
        print(learner.email, learner.status)
```

The first call trades your credentials for an Access token and asks the API
which Organization that token acts for. The client caches both answers, so
the second call goes straight to the endpoint you asked for.

`TeachMeHipaa` is a context manager, like `httpx.Client`. Leaving the `with`
block closes its connection pool. A client you keep for the life of a
process (most of them) can skip the `with` and call `client.close()` on the
way out.

## Read the response

Resources hang off the client as attributes (`client.learners`,
`client.enrollments`, `client.webhook_subscriptions`) and their methods
follow two rules:

- Ids from the URL path come first and positionally:
  `client.learners.retrieve("sub_01JD80AB2C3D4E5F6G7H8J9K0M")`.
- Everything else is a keyword argument, in snake_case: `course_id=`,
  `external_id=`, `seat_policy=`.

You get pydantic models back, with snake_case attributes and full type
hints, so your editor completes `learner.` for you. Every model also has
`last_response`, holding the HTTP `status`, `headers`, `request_id` and
`etag` of the response it came from.

A list method returns a page you can loop over. The loop runs across every
page and fetches the next one only when it gets there. See
[Pagination](pagination.md) for page-at-a-time control.

## Enroll a Learner

The samples from here on use a `client` built as above, without the `with`.

`learners.create` invites a Learner to a Course.
`learners.upsert_by_external_id` does the same, keyed by your own id for the
person (their External ID). Run the upsert from a nightly sync as often as
you like: the first run creates and invites the Learner, and later runs
return the same record. Both tell you which happened in `created`.

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

Each of these writes goes out with a generated `Idempotency-Key`, and a
retry reuses it, so a flaky network can't invite anyone twice.
[Retries and timeouts](retries-and-timeouts.md) explains when the client
retries.

## Where to go next

- [Async support](async.md): the same calls with `async`/`await`.
- [Authentication](authentication.md): Scopes, Live credentials and the
  Organization binding.
- [Webhooks](webhooks.md): hear about certifications as they happen.
- [Resource reference](../reference/resources.md): every method and its
  arguments.
