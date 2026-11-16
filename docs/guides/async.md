# Async support

`AsyncTeachMeHipaa` has the same constructor options, resources and methods
as `TeachMeHipaa`. You `await` each call, and the client sends requests
through an `httpx.AsyncClient`. Use it under asyncio: FastAPI, Starlette,
aiohttp servers, or any script that already runs an event loop.

## Make requests concurrently

<!-- sample: async -->
```python
import asyncio
import os

from teachmehipaa import AsyncTeachMeHipaa


async def main() -> None:
    async with AsyncTeachMeHipaa(
        client_id=os.environ["TMH_CLIENT_ID"],
        client_secret=os.environ["TMH_CLIENT_SECRET"],
        environment="sandbox",
    ) as client:
        learner, compliance = await asyncio.gather(
            client.learners.retrieve("sub_01JD80AB2C3D4E5F6G7H8J9K0M"),
            client.compliance.retrieve(),
        )
        print(learner.name, compliance.compliant_rate)

        async for item in await client.learners.list(limit=100):
            print(item.email)


asyncio.run(main())
```

`async with` closes the connection pool when the block ends. Without it,
`await client.close()` does the same.

Calls you start together share the client's setup: two coroutines that both
need an Access token wait on one token request, and the Organization lookup
happens once. Cancel a task (or let `asyncio.wait_for` time it out) and the
client cancels the HTTP request, any retries still pending and any `wait()`
on an Operation.

## Sync and async, side by side

The two clients differ only where Python's syntax makes them:

| `TeachMeHipaa`                                        | `AsyncTeachMeHipaa`                                                |
| ----------------------------------------------------- | ------------------------------------------------------------------ |
| `with TeachMeHipaa(...) as client:`                   | `async with AsyncTeachMeHipaa(...) as client:`                     |
| `client.close()`                                      | `await client.close()`                                             |
| `client.learners.retrieve(id)`                        | `await client.learners.retrieve(id)`                               |
| `for x in client.learners.list():`                    | `async for x in await client.learners.list():`                     |
| `page.get_next_page()`                                | `await page.get_next_page()`                                       |
| `for page in first.iter_pages():`                     | `async for page in first.iter_pages():`                            |
| `operation.wait()`                                    | `await operation.wait()`                                           |
| `with client.certificates.download_pdf(id, stream=True) as s:` | `async with await client.certificates.download_pdf(id, stream=True) as s:` |
| `for chunk in s.iter_bytes():`                        | `async for chunk in s.aiter_bytes():`                              |
| `for event in client.events.tail(...):`               | `async for event in client.events.tail(...):`                      |
| `stop=threading.Event()`                              | `stop=asyncio.Event()`                                             |
| `StaticTokenProvider`, `TokenProvider`                | `AsyncStaticTokenProvider`, `AsyncTokenProvider`                   |
| `http_client=httpx.Client(...)`                       | `http_client=httpx.AsyncClient(...)`                               |
| `sleep=time.sleep`                                    | `sleep=asyncio.sleep`                                              |

Return types follow the same pattern: list calls give you an `AsyncPage`,
Operations come back as `AsyncOperation` and streamed downloads as
`AsyncBinaryStream`. Models, errors and `Webhook` are shared by both.

`events.tail` is the one call you don't `await`: it returns an async
iterator straight away and makes its first request when you start the
`async for`.

## Wait for Operations and write files

`wait()` is a coroutine on `AsyncOperation`. Writing a file is still a
blocking call, so hand it to a thread with `asyncio.to_thread` and keep the
event loop free:

<!-- sample: async-files -->
```python
import asyncio
import os
from pathlib import Path

from teachmehipaa import AsyncTeachMeHipaa


async def main() -> None:
    async with AsyncTeachMeHipaa(
        client_id=os.environ["TMH_CLIENT_ID"],
        client_secret=os.environ["TMH_CLIENT_SECRET"],
        environment="sandbox",
    ) as client:
        operation = await client.certificates.export(format="csv")
        export = (await operation.wait(timeout=60)).export_result()
        await asyncio.to_thread(
            Path("certificates.csv").write_text, export.csv, newline=""
        )

        pdf = await client.certificates.download_pdf("cert_01JD8F3G5H7J9K1M3N5P7Q9R1S")
        await asyncio.to_thread(Path("certificate.pdf").write_bytes, pdf.content)


asyncio.run(main())
```

[Exports, imports and PDFs](files-and-operations.md) covers the Operation
and download APIs in full.

## Share one client in a FastAPI app

Build the client once, in the app's lifespan, and reuse it for every
request. One client keeps one connection pool and one cached Access token:

<!-- sample: async-fastapi -->
```python
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from teachmehipaa import AsyncTeachMeHipaa


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with AsyncTeachMeHipaa(
        client_id=os.environ["TMH_CLIENT_ID"],
        client_secret=os.environ["TMH_CLIENT_SECRET"],
        environment="sandbox",
    ) as client:
        app.state.tmh = client
        yield


app = FastAPI(lifespan=lifespan)


@app.get("/compliance")
async def compliance(request: Request) -> dict[str, float]:
    client: AsyncTeachMeHipaa = request.app.state.tmh
    summary = await client.compliance.retrieve()
    return {"compliant_rate": summary.compliant_rate}
```

The sync client guards its token and Organization lookup with a lock, so a
threaded Flask or Django app can share one module-level `TeachMeHipaa` in
the same way.
