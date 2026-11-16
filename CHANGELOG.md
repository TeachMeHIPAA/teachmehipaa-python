# Changelog

All notable changes to this library are documented here. It follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[semantic versioning](https://semver.org/).

## [Unreleased]

The first release, to ship as 1.0.0 when the Developer API launches.
Generated from the Developer API document release `trimmed-2026-11-15`.

### Added

- `TeachMeHipaa` and `AsyncTeachMeHipaa`, with the same surface, covering all
  44 Developer API operations as resources and pydantic models generated
  from the shared SDK IR: Learners, Enrollments, Certificates, Certificate
  verifications, Compliance, Courses, Members, Seats, Audit events, Webhook
  subscriptions, the Event log, Operations and `auth.introspect`. Both are
  context managers that close their `httpx` client.
- Client credentials authentication with cached, single-flight Access tokens
  renewed 60 s before expiry, and one renewal and replay on a 401.
- Live and Sandbox Environments, a `base_url` override, narrower `scopes`,
  and `StaticTokenProvider` / `AsyncStaticTokenProvider` for Access tokens
  obtained elsewhere. Public methods (`courses.*`,
  `certificate_verifications.retrieve`) send no token.
- A client without credentials, `TeachMeHipaa(environment="sandbox")` or
  `AsyncTeachMeHipaa(...)`, for public lookups such as Certificate
  verification. Any other call raises `ValueError` before sending a request;
  giving only one of `client_id` and `client_secret` still raises
  `TypeError`.
- The Organization binding: discovered once through `auth.introspect`, or
  given as `organization_id`.
- Typed errors by status (`InvalidRequestError`, `AuthenticationError`,
  `PermissionDeniedError`, `NotFoundError`, `ConflictError`,
  `PreconditionFailedError`, `IdempotencyError`, `RateLimitError`,
  `APIError`, `APIConnectionError`, `APITimeoutError`, `OAuthError`)
  carrying the problem `code`, `detail`, field `errors`, `headers` and
  `request_id`, with a guard that raises `APIError` for non-JSON responses
  instead of a parse error.
- Retries with exponential backoff and jitter for network errors, 409
  `conflict`, 429 and 5xx, honoring `Retry-After`, only for calls that are
  safe to replay; a generated `Idempotency-Key` per create and custom method,
  reused across retries and overridable per call; `max_retries` and
  `timeout` per client and per call; and a custom `request_id` per call
  (also on `events.tail` and `wait()`), sent as `x-request-id`.
- `last_response` on every returned object, with status, headers, request id
  and ETag.
- `SyncPage` and `AsyncPage`: iterate a list call's page (`for`, or
  `async for` after awaiting it) to get every item across pages, or use
  `items`, `next_cursor`, `has_next_page`, `get_next_page` and `iter_pages`.
- Conditional writes and reads with ETags (`if_match` takes an ETag or the
  object read; `if_none_match` returns a falsy `NotModified` on 304), and
  merge-patch updates that tell an omitted field (`NOT_GIVEN`) from one set
  to `None`. `if_match` is required on `learners.update` and
  `webhook_subscriptions.update`, which the API refuses without it.
- `Operation` and `AsyncOperation` with `wait()` and `export_result()` for
  export CSVs. Test delivery and redrive results are typed by `_tag`, with
  `UnknownWebhookDeliveryResult` for tags added later.
- Union variants type their discriminator as a `Literal` of their tag (such
  as `event_type: Literal["learner.certified"]`), so type checkers narrow on
  it once the `Unknown*` fallback, whose tag stays `str`, is ruled out.
- Enrollment CSV imports from a path, bytes or a binary file, and
  Certificate PDF downloads as a `BinaryResponse` or, with `stream=True`, a
  `BinaryStream` / `AsyncBinaryStream`.
- `Webhook.construct_event`, which verifies a Delivery's signature, body
  hash, path and timestamp and returns a typed Event, `UnknownEvent` or
  `TestDelivery`, accepting Flask's, Starlette's and Django's
  `request.headers`; and `Webhook.generate_test_headers` for testing
  handlers.
- `events.tail` to read the Event log from a saved position, once or
  following new Events, stoppable with a `threading.Event` or
  `asyncio.Event`.
- Opt-in DEBUG logging to the `teachmehipaa` logger, one record per response
  with method, path, status, latency and request id, never bodies, headers
  or credentials; a `User-Agent` with your `app_info`; and a pluggable
  `httpx` client.
- Python 3.10 to 3.13, fully typed (`py.typed`, checked with mypy in strict
  mode). No telemetry and no disk writes.

### Documentation

- Guides for partner developers in `docs/guides/`: getting started,
  authentication, errors and retries, pagination and Events, webhooks,
  Operations and files, conditional requests, testing, configuration and
  versioning. Every Python sample in them, as in the README, is
  type-checked and run against a fake of the API in CI.
- `docs/reference/resources.md`, generated from the SDK IR by
  `scripts/generate.py`: every resource and method with its signature, HTTP
  call, Scopes, retry, idempotency and conditional behavior, and return
  type, plus the Event types.
- An API reference built from the docstrings with pdoc, checked for
  warnings on every pull request and published to GitHub Pages from
  `main`.
- Runnable programs in `examples/`: a quickstart, a roster sync by External
  ID, a Flask webhook endpoint and a Certificate export.
- A shorter README with CI and license badges, a pre-release status note
  and links to the guides, and a docs index in `docs/README.md`.
