# Documentation

Documentation for `teachmehipaa`, the Python library for the TeachMeHIPAA
Developer API. Start with the [README](../README.md) for installation and a
quickstart.

## Guides

Every Python sample in these guides is type-checked with mypy and run
against a fake of the API in CI, so the samples work as written.

| Guide                                                    | Covers                                                                            |
| -------------------------------------------------------- | --------------------------------------------------------------------------------- |
| [Getting started](guides/getting-started.md)             | Install, Sandbox credentials, a first call, enrolling a Learner, the async client |
| [Authentication](guides/authentication.md)               | Client credentials, Scopes, Environments, the Organization binding, static tokens |
| [Errors and retries](guides/errors-and-retries.md)       | Error classes, `code`, request ids, retries, idempotency keys                     |
| [Pagination and Events](guides/pagination-and-events.md) | Iterating list calls, the Event log, `events.tail`                                |
| [Webhooks](guides/webhooks.md)                           | Webhook subscriptions, verifying Deliveries, Test deliveries, test headers        |
| [Operations and files](guides/operations-and-files.md)   | `wait()`, CSV exports and imports, Certificate PDFs                               |
| [Conditional requests](guides/conditional-requests.md)   | ETags, `if_match`, `if_none_match`, merge-patch updates                           |
| [Testing](guides/testing.md)                             | The Sandbox, a fake transport, signing test Deliveries                            |
| [Configuration](guides/configuration.md)                 | Every client option and its default, timeouts, logging                            |
| [Versioning](guides/versioning.md)                       | Semantic versioning, `OPENAPI_VERSION`, additive API changes                      |

## API reference

- [Resource reference](reference/resources.md): every resource and method,
  with its signature, HTTP call, required Scopes, retry and conditional
  behavior, and return type. Generated from the SDK IR by
  `scripts/generate.py`.
- [API reference](https://teachmehipaa.github.io/teachmehipaa-python/):
  every public class, function and model with its docstrings, built with
  [pdoc](https://pdoc.dev/) and published from `main`. Build it locally with
  the command in [CONTRIBUTING.md](../CONTRIBUTING.md#documentation).

## Examples

[`examples/`](../examples/) holds small programs you can run against the
Sandbox:

- [`quickstart.py`](../examples/quickstart.py): a first call.
- [`sync_roster.py`](../examples/sync_roster.py): sync a CSV roster with
  upserts by External ID.
- [`webhook_server.py`](../examples/webhook_server.py): a Flask endpoint
  that verifies Deliveries.
- [`export_certificates.py`](../examples/export_certificates.py): export
  Certificates to a CSV file.

## Contributing / design records

For people working on the library rather than with it:

- [CONTRIBUTING.md](../CONTRIBUTING.md): setup, checks, regeneration,
  releases and how these docs are built.
- [GLOSSARY.md](../GLOSSARY.md): the domain terms every SDK uses.
- [`adr/`](adr/): architecture decision records.
  - [0001](adr/0001-generated-surface-from-shared-ir.md) Hand-written core,
    generated surface from one shared IR
  - [0002](adr/0002-client-object-only.md) Instantiated client only, no
    global configuration
  - [0003](adr/0003-organization-bound-to-client.md) The Organization is
    bound to the client, not passed per call
  - [0004](adr/0004-refresh-tokens-are-never-retried.md) Refresh-token
    exchanges are never retried (superseded)
  - [0005](adr/0005-webhook-verification-needs-the-path.md) Webhook
    verification takes the request path, and Test deliveries are their own
    type
  - [0006](adr/0006-tolerant-models-open-enums.md) Models tolerate unknown
    fields and enums are open
  - [0007](adr/0007-no-telemetry-no-body-logging.md) No telemetry beyond
    User-Agent, and bodies are never logged
  - [0008](adr/0008-httpx-pydantic-two-clients.md) httpx and pydantic, with
    separate sync and async clients
- [`design/`](design/): the design grilling the SDKs were built from.
- [`research/`](research/): research into Stripe's Python library, whose
  conventions this library follows where they fit.
- [`agents/`](agents/): how coding agents work in this repository (issue
  tracker, triage labels, domain docs).
