# Changelog

All notable changes to this library are documented here. It follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[semantic versioning](https://semver.org/).

## [Unreleased]

The first release, to ship as 1.0.0 when the Developer API launches.
Generated from the Developer API document release `waggish-wombat`.

### Added

- `TeachMeHipaa` and `AsyncTeachMeHipaa`, with the same surface, covering all
  56 Developer API operations as resources and pydantic models generated
  from the shared SDK IR: Learners, Enrollments, Certificates, Certificate
  verifications, Compliance, Courses, Members, Seats, Seat orders, the
  payment method, Audit events, Webhook subscriptions, the Event log,
  Operations, `auth.introspect` and Partners. Both are context managers that
  close their `httpx` client.
- Client credentials authentication with cached, single-flight Access tokens
  renewed 60 s before expiry, and one renewal and replay on a 401.
- Live and Sandbox Environments, a `base_url` override, narrower `scopes`,
  and `StaticTokenProvider` / `AsyncStaticTokenProvider` for Access tokens
  obtained elsewhere. Public methods (`courses.*`,
  `certificate_verifications.retrieve`) send no token.
- The Organization binding: discovered once through `auth.introspect`, or
  given as `organization_id`.
- Typed errors by status (`InvalidRequestError`, `AuthenticationError`,
  `PermissionDeniedError`, `NotFoundError`, `ConflictError`,
  `PreconditionFailedError`, `IdempotencyError`, `RateLimitError`,
  `APIError`, `APIConnectionError`, `APITimeoutError`, `OAuthError`,
  `TokenStoreError`) carrying the problem `code`, `detail`, field `errors`,
  `headers` and `request_id`, with a guard that raises `APIError` for
  non-JSON responses instead of a parse error.
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
- Partner apps: `teachmehipaa.oauth` (PKCE pair, state, consent URL, code
  exchange) and `PartnerGrantTokenProvider` / `AsyncPartnerGrantTokenProvider`,
  which save every rotated Refresh token to your token store before use and
  never retry a Refresh token exchange. A client refuses a provider bound to
  another Environment or base URL.
- `events.tail` to read the Event log from a saved position, once or
  following new Events, stoppable with a `threading.Event` or
  `asyncio.Event`.
- Opt-in DEBUG logging to the `teachmehipaa` logger, one record per response
  with method, path, status, latency and request id, never bodies, headers
  or credentials; a `User-Agent` with your `app_info`; and a pluggable
  `httpx` client.
- Python 3.10 to 3.13, fully typed (`py.typed`, checked with mypy in strict
  mode). No telemetry and no disk writes.
