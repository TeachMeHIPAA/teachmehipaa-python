# TeachMeHIPAA Python Library

[![CI](https://github.com/TeachMeHIPAA/teachmehipaa-python/actions/workflows/ci.yml/badge.svg)](https://github.com/TeachMeHIPAA/teachmehipaa-python/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

The official Python library for the TeachMeHIPAA Developer API: enroll your
people in HIPAA training and track their compliance from your own systems.

> [!IMPORTANT]
> **Status: pre-release.** The Developer API isn't generally available yet,
> and this package isn't on PyPI. Until it is, install it from GitHub as
> shown below. Names and behavior can still change before 1.0.0.

The library handles Access tokens, the Organization binding, retries,
idempotency keys, typed errors, pagination, ETags, Operations and webhook
verification, so your code only calls methods. It has a synchronous client
and an asyncio client with the same methods, and ships type hints.

## Installation

Python 3.10 or newer. Install from GitHub:

```sh
pip install "teachmehipaa @ git+https://github.com/TeachMeHIPAA/teachmehipaa-python"
# or
uv add "teachmehipaa @ git+https://github.com/TeachMeHIPAA/teachmehipaa-python"
```

Once the package is on PyPI, this becomes `pip install teachmehipaa`.

## Quickstart

Create an API client in the TeachMeHIPAA console to get a client id
(`cli_…`) and secret (`tmh_cs_…`), and start in the Sandbox Environment:

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

The [getting started guide](docs/guides/getting-started.md) walks through
this step by step.

## Documentation

Guides, each with tested samples:

- [Getting started](docs/guides/getting-started.md): install, credentials,
  a first call, enrolling a Learner and the async client.
- [Authentication](docs/guides/authentication.md): client credentials,
  Scopes, Live and Sandbox Environments, the Organization binding, static
  Access tokens and public lookups without credentials.
- [Errors and retries](docs/guides/errors-and-retries.md): error classes,
  `code`, request ids, retries and idempotency keys.
- [Pagination and Events](docs/guides/pagination-and-events.md): iterating
  list calls, the Event log and `events.tail`.
- [Webhooks](docs/guides/webhooks.md): Webhook subscriptions, verifying
  Deliveries in Flask, FastAPI and Django, and Test deliveries.
- [Operations and files](docs/guides/operations-and-files.md): `wait()`,
  CSV exports and imports, and Certificate PDFs.
- [Conditional requests](docs/guides/conditional-requests.md): ETags,
  `if_match`, `if_none_match` and merge-patch updates.
- [Testing](docs/guides/testing.md): the Sandbox, a fake transport and
  signed test Deliveries.
- [Configuration](docs/guides/configuration.md): every client option,
  timeouts and logging.
- [Versioning](docs/guides/versioning.md): semantic versioning and how API
  changes reach the library.

Reference:

- [Resource reference](docs/reference/resources.md): every resource and
  method, with its HTTP call, Scopes and return type.
- [API reference](https://teachmehipaa.github.io/teachmehipaa-python/):
  every public class and function, built with pdoc.
- [Examples](examples/): small runnable programs.

The [docs index](docs/README.md) lists everything, design records included.

## Support and security

<!-- TODO(Nick): confirm the support address before launch. -->

For help, contact TeachMeHIPAA support and quote the `request_id` from the
error or `last_response`. To report a vulnerability, see
[SECURITY.md](SECURITY.md); please don't open a public issue.

See [CONTRIBUTING.md](CONTRIBUTING.md) to work on the library, and the
[changelog](CHANGELOG.md) for what changed. Licensed under the
[MIT License](LICENSE).
