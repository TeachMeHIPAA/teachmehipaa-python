# The Event log

An Event records something that happened in your Organization: a Learner
certified, an invite bounced, a Seat freed. The API keeps the last 30 days
of them in your Organization's Event log, oldest first. Read the log when
you want to poll, or to catch up on [webhook](webhooks.md) Deliveries you
missed. Reading it needs the `audit:read` or `webhooks:manage` Scope.
Samples use a `client` built as in the
[Quickstart](quickstart.md#make-a-request).

## List Events of one type

Every Event has an `event_id`, an `event_type`, an `occurred_at` datetime
and a `data` model that depends on the type. Narrow with `isinstance` and
your type checker knows exactly what `data` holds:

<!-- sample: events-list -->
```python
from teachmehipaa.types import EventLearnerCertified

for event in client.events.list(type="learner.certified"):
    if isinstance(event, EventLearnerCertified):
        print(event.data.email, event.occurred_at.date())
```

Each Event model also types `event_type` as a `Literal`, so once you've
ruled out `UnknownEvent`, a type checker narrows on `event.event_type` as
well. `events.list` also takes `after`, the id of the last Event you
handled, to start right after it. The
[resource reference](../reference/resources.md#event-types) maps each Event
type to its model.

TeachMeHIPAA adds Event types over time. An Event whose type this version of
the library doesn't know arrives as `UnknownEvent`, fields intact, so your
loop keeps running; give it an `else` branch.

## Follow the log from where you left off

`events.tail()` walks the log oldest first and tracks its own position in
`last_event_id`. Save that position as you go and pass it back as `after`
when your process restarts, and you resume exactly where you stopped. Here
`cursors` stands in for your own storage and `shutdown` is a
`threading.Event` your service sets on its way out:

<!-- sample: events-tail -->
```python
tail = client.events.tail(after=cursors.load(), follow=True, interval=5, stop=shutdown)
for event in tail:
    print(event.event_type, event.event_id)
    cursors.save(tail.last_event_id)
```

Leave out `follow` and the loop ends once it has caught up. With
`follow=True` it polls every `interval` seconds (2 by default) until you
`break` or set `stop`. On `AsyncTeachMeHipaa`, write `async for event in
client.events.tail(...)`, with no `await` in front of `tail`, and pass an
`asyncio.Event` as `stop`.

The log holds 30 days, so a consumer that stays down longer loses Events.
For Events as they happen, [subscribe to webhooks](webhooks.md) and keep the
tail for recovery.
