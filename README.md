# teachmehipaa

The official Python library for the TeachMeHIPAA Developer API.

> Pre-release. Nothing is published to PyPI yet.

```python
from teachmehipaa import TeachMeHipaa

with TeachMeHipaa(
    client_id="cli_...",
    client_secret="tmh_cs_...",
    environment="sandbox",
) as client:
    learner = client.learners.retrieve("sub_...")
    print(learner.status, learner.last_response.request_id)
```

`AsyncTeachMeHipaa` has the same surface with `await`.

## Pagination

A list method returns one page (`.items`, `.next_cursor`). Iterating the page
fetches the pages after it lazily, until `next_cursor` is `None`, and stops
fetching when you break out of the loop:

```python
for learner in client.learners.list(status="in_progress", limit=100):
    print(learner.email)
```

With `AsyncTeachMeHipaa`, await the call for the first page and `async for`
over it, as in Stripe's library:

```python
async for learner in await client.learners.list():
    print(learner.email)
```

`page.has_next_page()`, `page.get_next_page()` and `page.iter_pages()` work a
page at a time; `auto_paging_iter()` is an alias for iterating.

`client.events.tail(after=last_event_id)` yields only Events newer than
`after` and keeps its position in `tail.last_event_id`; save it to resume
after a restart. With `follow=True` it polls every `interval` seconds
(default 2) until you break or set `stop` (a `threading.Event`, or an
`asyncio.Event` on the async client, where the tail is iterated with
`async for` and no `await`).
