# Conditional requests

Resources carry a strong ETag that changes whenever the resource does. The
library reads it into `last_response.etag` and sends it back for you, to
stop an update from overwriting a change you haven't seen, and to skip
re-downloading something that hasn't changed.

Samples assume a `client` created as in
[Getting started](getting-started.md#3-make-your-first-call).

## Conditional updates with `if_match`

Updates that the API guards with ETags take `if_match`: the ETag string, or
the object you read, whose `last_response.etag` the client sends.

| Method                         | `if_match` |
| ------------------------------ | ---------- |
| `learners.update`              | Required   |
| `webhook_subscriptions.update` | Required   |
| `learners.offboard`            | Optional   |

If the resource changed since you read it, the call raises
`PreconditionFailedError` (412): read it again, reapply your change and
retry. The API refuses a required `if_match` that is missing with 428,
which raises `PreconditionFailedError` too, but the type checker catches
that first, since the argument is required. `"*"` matches any version.

## Merge-patch updates

Updates are JSON merge patches. An argument you leave out (or pass as
`NOT_GIVEN`) is not sent and stays unchanged; `None` is sent as JSON `null`
and clears the field.

<!-- sample: conditional-write -->
```python
from teachmehipaa import PreconditionFailedError

learner = client.learners.retrieve("sub_01JD80AB2C3D4E5F6G7H8J9K0M")
try:
    updated = client.learners.update(
        learner.learner_id,
        if_match=learner,
        name="Ana Q. Example",
        external_id=None,
    )
    print(updated.name)
except PreconditionFailedError:
    print("Someone else changed this Learner; read it again")
```

Here `name` changes, `external_id` is cleared, and every other field stays
as it was. Updates are never retried, since replaying one could undo
someone else's change.

## Conditional reads with `if_none_match`

`courses.retrieve`, `enrollments.retrieve` and
`webhook_subscriptions.retrieve` take `if_none_match`: the ETag of the copy
you hold, or that copy itself. When your copy is still current, the API
answers 304 and the method returns `NotModified` instead of a new copy.
`NotModified` is falsy, so `or` picks your copy:

<!-- sample: not-modified -->
```python
from teachmehipaa import NotModified

course = client.courses.retrieve("hipaa-2026")

latest = client.courses.retrieve("hipaa-2026", if_none_match=course)
if isinstance(latest, NotModified):
    print("still current")
course = latest or course
print(course.title)
```

Without `if_none_match`, these methods are typed to return the model alone,
so you only handle `NotModified` where it can happen.
