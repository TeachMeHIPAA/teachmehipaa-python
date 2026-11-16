# Retries and timeouts

The client retries a failed call when replaying it can't do harm, and gives
up on a response after 80 seconds. You can change both per client and per
call. Samples use a `client` built as in the
[Quickstart](quickstart.md#make-a-request).

## When the client retries

A call is retried after a network error, a 409 with code `conflict`, a 429
or any 5xx, up to `max_retries` times (2 unless you say otherwise). Between
attempts it backs off exponentially from 0.5 s to a cap of 5 s, with jitter,
and when the API sends `Retry-After` it waits that long instead, up to 60 s.

It only retries a call that is safe to replay:

- any read;
- a write that carries an `Idempotency-Key`;
- a write the API defines as idempotent, such as
  `learners.create_launch_link`.

PATCH and DELETE never retry. The
[resource reference](../reference/resources.md) marks each method
"Retried on …" or "Never retried".

Once the retries run out you get the last error. If that's a
`RateLimitError` and the API sent `Retry-After`, `error.retry_after` holds
the wait it asked for, in seconds.

## Make a write safe to repeat

Every POST and PUT goes out with a generated UUID `Idempotency-Key`, except
`learners.create_launch_link`, which the API treats as idempotent anyway.
Retries reuse the key, so a lost response never leads the API to enroll a
Learner twice.

A generated key only lives as long as one call. When a job might run twice,
say a cron sync that a deploy restarts, pass your own `idempotency_key`
built from something stable. For 24 hours the API answers a repeated key
and body with the first response and skips the work. The same key with a
different body raises `IdempotencyError`. PATCH and DELETE take no key; the
API would ignore it.

## Override settings for one call

Every method accepts `max_retries`, `timeout` and `request_id` as keyword
arguments, on top of its own:

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

`request_id` travels as `x-request-id` on every attempt, so all the retries
show up under one id in your logs and TeachMeHIPAA's (see
[Exceptions](exceptions.md#quote-a-request-id-to-support)).

## Set timeouts

`timeout` is how long the client waits for each response: 80 seconds by
default. A float covers every phase of the request. An `httpx.Timeout` sets
them one by one, the usual choice being a short connect timeout and a longer
read timeout:

<!-- sample: timeouts -->
```python
import httpx

page = client.learners.list(timeout=httpx.Timeout(30.0, connect=5.0), max_retries=0)
print(len(page.items))
```

Pass the same value to `TeachMeHipaa(timeout=...)` to make it the default.
A call that hears nothing back in time raises `APITimeoutError` once its
retries are spent. `wait()` on an Operation has its own `timeout` and
`interval`, covered in [Exports, imports and PDFs](files-and-operations.md).
