# Safe updates with ETags

Learners, Enrollments, Courses and Webhook subscriptions carry a strong ETag
that changes whenever the resource does. The client stores it on
`last_response.etag` and sends it back when you ask, which gives you two
things: an update that refuses to overwrite a change you haven't seen, and
a read that skips the download when your copy is current. Samples use a
`client` built as in the [Quickstart](quickstart.md#make-a-request).

## Update without clobbering someone else's change

Pass `if_match` to an update: either the ETag string or the model you read,
in which case the client sends that model's `last_response.etag`.

| Method                         | `if_match` |
| ------------------------------ | ---------- |
| `learners.update`              | Required   |
| `webhook_subscriptions.update` | Required   |
| `learners.offboard`            | Optional   |

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

If the Learner changed after your read, the API answers 412 and you get
`PreconditionFailedError`: read again, reapply your change, try again. The
API answers 428 to an update with no `if_match`, which raises the same
error, but mypy flags the missing argument long before that because the
signature requires it. `if_match="*"` matches any version, for the rare
write that should win regardless.

## Change some fields and clear others

Updates are JSON merge patches, and the method signature maps onto them
directly:

- leave an argument out (or pass `NOT_GIVEN`) and the field isn't sent, so
  it keeps its value;
- pass `None` and the client sends JSON `null`, which clears the field.

So the sample above sets `name`, clears `external_id` and touches nothing
else. The client never retries an update, since a replay could undo a
change someone made in between.

## Skip the download when nothing changed

`courses.retrieve`, `enrollments.retrieve` and
`webhook_subscriptions.retrieve` take `if_none_match`, given as the ETag of
the copy you hold or as the copy itself. If your copy is current the API
answers 304 and the method returns `NotModified`. `NotModified` is falsy,
so `or` falls back to your copy:

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

The return type follows the argument. Call without `if_none_match` and the
overloads type the result as `Course`; add it and you get
`Course | NotModified`, so you only handle `NotModified` where it can
happen.
