# Pagination and Events

List calls return one page at a time, and the library fetches the rest as
you iterate. The Event log is a list too, with a helper that follows it as
new Events arrive.

Samples assume a `client` created as in
[Getting started](getting-started.md#3-make-your-first-call).

## Iterating a list call

A list method returns one page, with `items` and `next_cursor`. Iterating
the page yields every item across all pages, fetching the next page only
when the loop reaches it, and stops fetching when you `break`. `limit` sets
the page size: 20 by default, and at most 100 (1,000 for Enrollments and
Members).

<!-- sample: pagination -->
```python
# Every Learner, page by page, fetched lazily.
for learner in client.learners.list(limit=100):
    print(learner.learner_id)

# One page at a time.
page = client.enrollments.list(limit=50)
print(len(page.items))
while page.has_next_page():
    page = page.get_next_page()
    print(len(page.items))
```

`page.iter_pages()` yields each page in turn, and `auto_paging_iter()` is an
alias for iterating the page, as in Stripe's library. Filters you pass to
the first call, such as `status`, apply to every page.

On the async client, await the list call for its first page, then
`async for` over it:

<!-- sample: async-pagination -->
```python
from teachmehipaa import AsyncTeachMeHipaa


async def print_emails(client: AsyncTeachMeHipaa) -> None:
    async for learner in await client.learners.list(limit=100):
        print(learner.email)
```

`get_next_page()` and `iter_pages()` are awaited and async-iterated the
same way.

## The Event log

An Event records that something happened in your Organization, such as a
Learner being certified. The Organization's Event log keeps Events for 30
days, oldest first. Every Event has an `event_id`, an `event_type`, an
`occurred_at` time and `data` whose model depends on the type; the
[resource reference](../reference/resources.md#event-types) lists the types
and their models.

`events.list` reads the log. Pass `type` to read one Event type, and
`after` to start after an Event you already handled. Tell Events apart with
`isinstance` or by `event_type`:

<!-- sample: events-list -->
```python
from teachmehipaa.types import EventLearnerCertified

for event in client.events.list(type="learner.certified"):
    if isinstance(event, EventLearnerCertified):
        print(event.data.email, event.occurred_at.date())
```

New Event types are added over time. An Event of a type this version of
the library doesn't know arrives as `UnknownEvent`, with its fields kept,
so it never breaks your loop. Reading the log needs the `audit:read` or
`webhooks:manage` Scope.

## Tailing the Event log

`events.tail` reads the Event log oldest first and keeps its own position
in `last_event_id`. Save it, and resume from it after a restart to catch up
on anything you missed while down, without webhooks. Here `cursors` stands
in for your own storage and `shutdown` is a `threading.Event` your service
sets when it stops:

<!-- sample: events-tail -->
```python
tail = client.events.tail(after=cursors.load(), follow=True, interval=5, stop=shutdown)
for event in tail:
    print(event.event_type, event.event_id)
    cursors.save(tail.last_event_id)
```

Without `follow`, the loop ends once it has caught up. With it, the tail
polls every `interval` seconds until you `break` or set `stop`. On the
async client, iterate with `async for` (no `await` before `tail`) and pass
an `asyncio.Event` as `stop`.

The log keeps 30 days of Events, so a consumer that is down longer than
that misses Events. For Events as they happen, subscribe to them with
[webhooks](webhooks.md); the log and `tail` are the way to catch up on
Deliveries you missed.
