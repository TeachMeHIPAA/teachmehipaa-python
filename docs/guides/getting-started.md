# Getting started

This guide takes you from an empty project to calls against the Sandbox:
reading your Organization's compliance, listing Learners and enrolling one.

## Requirements

Python 3.10 or newer. The library depends on `httpx` and `pydantic` 2, and
ships type hints (`py.typed`).

## 1. Install the library

> [!IMPORTANT]
> The Developer API isn't generally available yet and the package isn't on
> PyPI. Until it is, install it from GitHub.

```sh
pip install "teachmehipaa @ git+https://github.com/TeachMeHIPAA/teachmehipaa-python"
# or
uv add "teachmehipaa @ git+https://github.com/TeachMeHIPAA/teachmehipaa-python"
```

## 2. Get Sandbox credentials

An Organization admin creates an API client in the TeachMeHIPAA console.
It has a client id (`cli_…`) and a secret (`tmh_cs_…`) and belongs to one
Organization in one Environment. Create it in the **Sandbox** Environment
while you build: no real Learners are emailed there, and Sandbox
credentials never work against Live.

Keep the secret out of your code. The samples read both values from
environment variables:

```sh
export TMH_CLIENT_ID=cli_...
export TMH_CLIENT_SECRET=tmh_cs_...
```

## 3. Make your first call

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

On the first call the client exchanges your credentials for an Access
token, then asks the API which Organization the token belongs to. It
caches both, so later calls go straight to the API. The `with` block
closes the client's connection pool; without it, call `client.close()`
when you're done.

Methods take keyword arguments, except ids in the path, which come first
and positionally: `client.learners.retrieve(learner_id)`. They return
pydantic models with snake_case attributes, and every model has a
`last_response` with the HTTP `status`, `headers`, `request_id` and `etag`.

Iterating a list call yields every item across all pages; see
[Pagination and Events](pagination-and-events.md).

## 4. Enroll a Learner

Samples from here on assume a `client` created as in step 3, without the
`with` block.

`learners.create` invites a Learner to a Course. `upsert_by_external_id`
does the same keyed by your own id for the Learner (their External ID), so
a sync job can run it again and again: it creates and invites the Learner
the first time and returns them every time after. Both say whether they
created the Learner in `created`.

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

The client sends an `Idempotency-Key` with each of these writes and reuses
it if it retries, so a retry never invites a Learner twice. See
[Errors and retries](errors-and-retries.md).

## 5. Use the async client

`AsyncTeachMeHipaa` takes the same options and has the same methods; await
each call. Await a list call for its first page, then `async for` over it
to get every item:

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

## Next steps

- [Authentication](authentication.md): Scopes, Live credentials and the
  Organization binding.
- [Webhooks](webhooks.md): hear about certifications as they happen.
- [Resource reference](../reference/resources.md): every method.
- [`examples/`](../../examples/): complete programs to copy from.
