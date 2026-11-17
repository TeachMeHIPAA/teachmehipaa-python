# Documentation

The API reference and guides for `teachmehipaa`, the Python client for the
TeachMeHIPAA Developer API, live at
[docs.teachmehipaa.com/api](https://docs.teachmehipaa.com/api?lang=python).
The [README](../README.md) has the install command and a first request.

## Code samples

[`code-samples.json`](reference/code-samples.json) holds one Python sample
per API operation, written by `scripts/generate.py`. The hosted API
reference shows them when you pick Python.

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

- [CONTRIBUTING.md](../CONTRIBUTING.md): setup, checks, regeneration and
  releases.
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
