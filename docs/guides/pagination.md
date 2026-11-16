# Pagination

List methods return one page of results. Loop over the page and the library
fetches the following pages as your loop reaches them. Samples use a
`client` built as in the [Quickstart](quickstart.md#make-a-request).

## Loop over every item

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

The first loop asks for the next page only when it runs out of items, and a
`break` stops the fetching. Filters on the first call, such as `status`, hold
for every page.

`limit` is the page size: 20 if you leave it out, at most 100, and at most
1,000 for `enrollments.list` and `members.list`. It changes how many
requests a full loop makes, never which items you get.

## Work a page at a time

A page is a `SyncPage` (an `AsyncPage` on the async client) with:

- `items`: the list of models on this page;
- `next_cursor`: the cursor for the next page, or `None` on the last one;
- `has_next_page()` and `get_next_page()`, as in the sample above;
- `iter_pages()`: a generator over this page and every page after it;
- `auto_paging_iter()`: the same iterator a `for` loop gets, under the name
  Stripe's Python library uses;
- `last_response`: the HTTP details of the request that fetched this page.

Reach for `iter_pages()` when you write in batches, such as one database
transaction per page.

## Paginate with asyncio

Await the list call to get the first page, then `async for` over it:

<!-- sample: async-pagination -->
```python
from teachmehipaa import AsyncTeachMeHipaa


async def print_emails(client: AsyncTeachMeHipaa) -> None:
    async for learner in await client.learners.list(limit=100):
        print(learner.email)
```

The `await` fetches the first page and the `async for` fetches the rest.
`get_next_page()` is a coroutine, and `iter_pages()` is an async generator,
so it takes `async for` too. [Async support](async.md#sync-and-async-side-by-side)
lists every place the two clients differ.

The Event log pages differently (by the last Event's id instead of a
cursor) but you loop over it the same way; see [The Event log](events.md).
