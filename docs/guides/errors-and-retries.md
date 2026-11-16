# Errors and retries

The client retries what is safe to retry, and raises a typed error for
everything else. This guide covers what it raises, what each error carries,
and how retries and idempotency keys keep a retried write from happening
twice.

Samples assume a `client` created as in
[Getting started](getting-started.md#3-make-your-first-call).

## Error classes

Failed calls raise a subclass of `TeachMeHipaaError`, chosen by HTTP
status. All of them can be imported from `teachmehipaa`.

| Class                     | When                                                      |
| ------------------------- | --------------------------------------------------------- |
| `InvalidRequestError`     | 400, 405, 406, 415 and 422                                |
| `IdempotencyError`        | 422 `idempotency_key_reuse` (an `InvalidRequestError`)    |
| `AuthenticationError`     | 401                                                       |
| `PermissionDeniedError`   | 403, such as a missing Scope                              |
| `NotFoundError`           | 404                                                       |
| `ConflictError`           | 409                                                       |
| `PreconditionFailedError` | 412 (stale ETag) and 428 (missing `if_match`)             |
| `RateLimitError`          | 429, with `retry_after` in seconds                        |
| `APIError`                | 5xx, or a response that isn't JSON (such as an HTML page) |
| `APIConnectionError`      | No response arrived                                       |
| `APITimeoutError`         | No response within `timeout` (an `APIConnectionError`)    |
| `OAuthError`              | The token endpoint refused to issue a token               |

Three more come from specific features: `OperationFailedError` and
`OperationTimeoutError` from `wait()` (see
[Operations and files](operations-and-files.md)), and
`WebhookSignatureError` from webhook verification (see
[Webhooks](webhooks.md)).

The names follow PEP 8 (`APIError`, not `ApiError`). A client without
credentials raises `ValueError` for a method that needs them, and invalid
client options raise `TypeError` or `ValueError` when you create the
client; neither is a `TeachMeHipaaError`, since neither comes from the API.

## What an error carries

Each `TeachMeHipaaError` has:

- `code`: the problem's machine-readable code, such as `not_found` or
  `external_id_conflict`. Branch on it rather than on `detail`. New codes
  can appear at any time, so keep a fallback.
- `title` and `detail`: what went wrong, for people.
- `errors`: field-level problems, each with a `path` and `message`.
- `status`, `headers` and `request_id`: from the HTTP response.
- `message`: the most specific of `detail`, `title` and `code`.
  `str(error)` adds the request id to it.

<!-- sample: errors -->
```python
from teachmehipaa import NotFoundError, PermissionDeniedError, TeachMeHipaaError

try:
    client.learners.retrieve("sub_01JD80AB2C3D4E5F6G7H8J9K0M")
except NotFoundError:
    print("No such Learner")
except PermissionDeniedError as error:
    print("Missing a Scope:", error.detail)
except TeachMeHipaaError as error:
    print(error.code, error.detail, error.request_id)
    for field in error.errors:
        print(field.path, field.message)
```

## Request ids

Every response carries a request id, on `error.request_id` for a failure
and on `last_response.request_id` for a success. Quote it to TeachMeHIPAA
support and they can find the call.

To use your own, pass `request_id`: the client sends it as `x-request-id`
on every attempt of the call, so the call can be found in your logs and
TeachMeHIPAA's under the same id. The API echoes an id that matches
`^[A-Za-z0-9._-]{1,128}$` and replaces any other.

## Retries

The client retries network errors, 409 `conflict`, 429 and 5xx up to
`max_retries` times (2 by default). It backs off exponentially from 0.5 s
up to 5 s with jitter, and honors `Retry-After` up to 60 s. It only retries
calls that are safe to replay:

- reads;
- writes that carry an `Idempotency-Key`;
- the few writes that are idempotent by nature, such as
  `learners.create_launch_link`.

PATCH and DELETE are never retried. The
[resource reference](../reference/resources.md) says for each method
whether it is retried.

When the retries run out, the last error is raised. A `RateLimitError`
then has `retry_after`, the seconds the API asked you to wait, if it sent
`Retry-After`.

## Idempotency keys

Every create and custom method gets a generated UUID `Idempotency-Key`,
reused by each of its retries, so a retry never enrolls a Learner twice.
Pass your own `idempotency_key` to make a call safe to repeat across
processes too, such as a sync job that may run twice for the same day.
For 24 hours, the API answers a repeat of a key and body with the first
response, without doing the work again; reusing a key with a different body
raises `IdempotencyError`. PATCH and
DELETE take no key: the API ignores one on them.

`max_retries` and `timeout` (in seconds) override the client's settings for
one call:

<!-- sample: request-options -->
```python
enrollment = client.enrollments.create(
    email="ana@example.com",
    course_id="hipaa-2026",
    idempotency_key="hr-sync-2026-11-15-ana",
    max_retries=5,
    timeout=10.0,
    request_id="hr-sync-2026-11-15-ana",
)
print(enrollment.enrollment_id, enrollment.last_response.request_id)
```
