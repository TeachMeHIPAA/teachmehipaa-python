# teachmehipaa

[![CI](https://github.com/TeachMeHIPAA/teachmehipaa-python/actions/workflows/ci.yml/badge.svg)](https://github.com/TeachMeHIPAA/teachmehipaa-python/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A typed Python client for the TeachMeHIPAA Developer API. Enroll your
people in HIPAA training, track who is compliant and collect their
Certificates from your own HR system, scripts or web app.

> [!NOTE]
> **Pre-release.** The Developer API isn't generally available yet and
> `teachmehipaa` isn't on PyPI. Install it from GitHub for now, and expect
> names and behavior to change before 1.0.0.

```sh
pip install "teachmehipaa @ git+https://github.com/TeachMeHIPAA/teachmehipaa-python"
```

Python 3.10+. Once it reaches PyPI, `pip install teachmehipaa` will do.

## A quick look

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

The same calls work under asyncio. Swap in `AsyncTeachMeHipaa` and `await`:

<!-- sample: readme-async -->
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
        learner = await client.learners.retrieve("sub_01JD80AB2C3D4E5F6G7H8J9K0M")
        print(learner.name, learner.status)


asyncio.run(main())
```

Get a client id (`cli_…`) and secret (`tmh_cs_…`) by creating an API client
in the TeachMeHIPAA console, in the Sandbox Environment while you build.

## What you get

- **Sync and async clients** with identical methods, built on `httpx`, both
  usable as context managers.
- **Type hints throughout**: responses are pydantic models, nested request
  bodies are `TypedDict`s, and the package passes mypy in strict mode.
  Keyword arguments mirror the API's fields in snake_case.
- **Token handling**: the client fetches and renews Access tokens and works
  out which Organization they act for.
- **Retries with backoff** on 429, 5xx and network errors. Creates and
  actions carry an idempotency key, so a retry never enrolls someone twice.
- **Lazy pagination**: `for learner in client.learners.list():` walks every
  page.
- **Helpers for the awkward parts**: ETag-guarded updates, Operations with
  `wait()`, CSV exports and imports, streamed PDF downloads, webhook
  signature checks for Flask, FastAPI and Django, and an Event log tail.

## Documentation

Start with the [Quickstart](docs/guides/quickstart.md), then pick what you
need:

| Guide                                                      | Read it to                                                     |
| ---------------------------------------------------------- | -------------------------------------------------------------- |
| [Quickstart](docs/guides/quickstart.md)                    | Install, get Sandbox credentials, make requests, enroll someone |
| [Async support](docs/guides/async.md)                      | Use `AsyncTeachMeHipaa`, run calls concurrently, share a client in FastAPI |
| [Authentication](docs/guides/authentication.md)            | Narrow Scopes, switch Environments, bring your own tokens      |
| [Pagination](docs/guides/pagination.md)                    | Loop over list calls or work a page at a time                  |
| [Exceptions](docs/guides/exceptions.md)                    | Catch errors and read their `code` and request id              |
| [Retries and timeouts](docs/guides/retries-and-timeouts.md) | Tune retries, timeouts and idempotency keys                   |
| [Safe updates with ETags](docs/guides/etags.md)            | Update without overwriting changes, skip unchanged reads       |
| [Exports, imports and PDFs](docs/guides/files-and-operations.md) | Wait for Operations, move CSV files, download Certificates |
| [The Event log](docs/guides/events.md)                     | List Events and tail the log from a saved position            |
| [Webhooks](docs/guides/webhooks.md)                        | Subscribe, then verify Deliveries in Flask, FastAPI or Django  |
| [Testing](docs/guides/testing.md)                          | Unit-test with a mock transport, sign test Deliveries          |
| [Advanced usage](docs/guides/advanced-usage.md)            | Every client option, custom `httpx` clients, logging          |
| [Versions and compatibility](docs/guides/compatibility.md) | Supported Pythons, semver, surviving API additions            |

Every Python block in the README and the guides runs in CI: mypy
type-checks it and the test suite executes it against a fake API.

For lookups, the [resource reference](docs/reference/resources.md) lists
every method with its HTTP call, Scopes and return type, and the
[API reference](https://teachmehipaa.github.io/teachmehipaa-python/) has
every class and docstring, built with pdoc. [`examples/`](examples/) holds
small programs you can run against the Sandbox. The
[docs index](docs/README.md) links everything, design records included.

## Support and security

<!-- TODO(Nick): confirm the support address before launch. -->

For help, contact TeachMeHIPAA support and include the `request_id` from the
exception or from `last_response`. Report vulnerabilities privately, as
[SECURITY.md](SECURITY.md) describes.

To hack on the library itself, see [CONTRIBUTING.md](CONTRIBUTING.md).
Changes are in the [changelog](CHANGELOG.md). MIT
[licensed](LICENSE).
