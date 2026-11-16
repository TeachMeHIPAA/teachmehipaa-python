# Documentation

Everything written about `teachmehipaa`, the Python client for the
TeachMeHIPAA Developer API. New here? The [README](../README.md) has the
install command and a first request.

## Guides

Read them roughly in this order. CI type-checks every Python sample in them
with mypy and runs it against a fake of the API.

| Guide                                                    | Covers                                                                 |
| -------------------------------------------------------- | ---------------------------------------------------------------------- |
| [Quickstart](guides/quickstart.md)                       | Install, Sandbox credentials, a first request, enrolling a Learner     |
| [Async support](guides/async.md)                         | `AsyncTeachMeHipaa`, `asyncio.gather`, sync/async cheat sheet, FastAPI |
| [Authentication](guides/authentication.md)               | Client credentials, Scopes, Environments, token providers              |
| [Pagination](guides/pagination.md)                       | `for` over list calls, page objects, `async for`                       |
| [Exceptions](guides/exceptions.md)                       | The exception tree, `code`, request ids                                |
| [Retries and timeouts](guides/retries-and-timeouts.md)   | Retry rules, idempotency keys, per-call options, `httpx.Timeout`       |
| [Safe updates with ETags](guides/etags.md)               | `if_match`, merge patches, `if_none_match` and `NotModified`           |
| [Exports, imports and PDFs](guides/files-and-operations.md) | `wait()`, CSV exports and imports, Certificate PDFs                 |
| [The Event log](guides/events.md)                        | `events.list`, `events.tail`                                           |
| [Webhooks](guides/webhooks.md)                           | Subscriptions, verifying Deliveries in Flask/FastAPI/Django, Test deliveries |
| [Testing](guides/testing.md)                             | `httpx.MockTransport`, signed test Deliveries, Sandbox runs            |
| [Advanced usage](guides/advanced-usage.md)               | Every client option, custom `httpx` clients, User-Agent, logging       |
| [Versions and compatibility](guides/compatibility.md)    | Supported Pythons, semver, `OPENAPI_VERSION`, additive API changes     |

## API reference

- [Resource reference](reference/resources.md): every resource and method,
  with its signature, HTTP call, required Scopes, retry and conditional
  behavior, and return type. `scripts/generate.py` writes it from the SDK
  IR.
- [`code-samples.json`](reference/code-samples.json): one Python sample per
  API operation, also written by `scripts/generate.py`. The TeachMeHIPAA API
  reference shows them when you pick Python.
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
