# Security policy

<!-- TODO(Nick): confirm the reporting address and response times before launch. -->

## Reporting a vulnerability

Please report security issues privately to **security@teachmehipaa.com**, not
in a public GitHub issue. Include the library version, what you found and,
if you can, steps to reproduce it. Don't include real Learner data, Access
tokens, client secrets or Signing secrets in the report.

We will acknowledge your report, keep you informed while we fix it, and
credit you in the release notes if you would like.

## Supported versions

Security fixes are released for the latest major version.

## How the library handles secrets and Learner data

- It sends no telemetry and writes nothing to disk.
- It never logs request or response bodies, headers or credentials; its
  opt-in DEBUG logging records only the method, path, status, latency and
  request id (ADR-0007).
- `WebhookSignatureError` never carries the Delivery's body or headers.
- It is server-side only: never ship a client secret to a browser or a mobile
  app.
