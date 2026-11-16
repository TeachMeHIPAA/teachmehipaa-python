# Configuration

A client's options are keyword arguments to `TeachMeHipaa` (or
`AsyncTeachMeHipaa`), fixed when you create it. There is no global
configuration: two clients with different settings can live side by side.

<!-- sample: configuration -->
```python
import os

import httpx

from teachmehipaa import TeachMeHipaa

client = TeachMeHipaa(
    client_id=os.environ["TMH_CLIENT_ID"],
    client_secret=os.environ["TMH_CLIENT_SECRET"],
    environment="sandbox",
    scopes=["learners:read", "learners:write"],
    organization_id="org_acme",
    max_retries=3,
    timeout=30.0,
    app_info={
        "name": "acme-hr-sync",
        "version": "4.2.0",
        "url": "https://acme.example",
    },
    http_client=httpx.Client(timeout=30.0),
)
print(client.environment, client.base_url, client.max_retries)
```

## Options

| Option            | Default                               | Description                                                                          |
| ----------------- | ------------------------------------- | ------------------------------------------------------------------------------------ |
| `client_id`       | None: public methods only             | Your API client's id (`cli_…`)                                                       |
| `client_secret`   | Required with `client_id`             | The matching secret (`tmh_cs_…`)                                                     |
| `scopes`          | Every Scope the API client holds      | Narrows the Access token's Scopes                                                    |
| `token_provider`  | Client credentials                    | Supplies Access tokens instead, such as a `StaticTokenProvider`                      |
| `environment`     | `"live"`                              | `"live"` or `"sandbox"`; credentials work only in their own Environment              |
| `base_url`        | The Environment's URL                 | Overrides it, e.g. to point at a mock server                                         |
| `organization_id` | Looked up once with `auth.introspect` | The Organization to act for                                                          |
| `max_retries`     | `2`                                   | Retries of a failed call that is safe to replay                                      |
| `timeout`         | `80.0`                                | Seconds to wait for each response; a float or an `httpx.Timeout`                     |
| `app_info`        | None                                  | `{"name": ..., "version": ..., "url": ...}` of your software, sent in the User-Agent |
| `http_client`     | A new `httpx.Client` (`AsyncClient`)  | Sends requests, e.g. with a proxy, mTLS or a mock transport; closed by `close()`     |
| `clock`, `sleep`  | `time.monotonic`, `time.sleep`        | Supply the time and waits, for tests (`asyncio.sleep` on the async client)           |

Pass either `client_id` and `client_secret`, or `token_provider`, not both;
`scopes` then belong to the token provider. With neither, the client makes
only public calls (see [Authentication](authentication.md)). The base URLs
are `https://api.tme.so/v1` for Live and
`https://api-teachmehipaa-dev.web.app/v1` for the Sandbox.
`environment`, `base_url`, `max_retries` and `timeout` can be read back from
the client.

## Timeouts

`timeout` is how long to wait for each response, 80 seconds by default. A
float applies to every phase of the request; an `httpx.Timeout` sets them
separately, such as a short connect timeout with a longer read timeout.
`max_retries`, `timeout` and `request_id` can also be given to any one
call, overriding the client's settings for that call (this sample, like
the logging one below, assumes a `client` created as in
[Getting started](getting-started.md#3-make-your-first-call)):

<!-- sample: timeouts -->
```python
import httpx

page = client.learners.list(timeout=httpx.Timeout(30.0, connect=5.0), max_retries=0)
print(len(page.items))
```

A call that gets no response in time raises `APITimeoutError`, after any
retries. An Operation's `wait()` has its own `timeout` and `interval` for
how long and how often to poll; see
[Operations and files](operations-and-files.md).

## Your own `httpx` client

Pass `http_client` to send requests through an `httpx.Client` you
configured, for a proxy, custom certificates or mTLS, or a mock transport
in tests (see [Testing](testing.md)). The client's `close()`, or leaving its
`with` block, closes it. Use `httpx.AsyncClient` with `AsyncTeachMeHipaa`.

## Identifying your software

`app_info` adds your software's name, and optionally its version and URL,
to the `User-Agent` the client sends, after the library's own
`teachmehipaa-python/<version> python/<version> httpx/<version>`. It helps
TeachMeHIPAA support find your calls. The library sends no other telemetry.

## Logging

The library prints nothing, sends no telemetry and writes nothing to disk.
It logs through the standard `logging` module, to the logger named
`teachmehipaa`: one DEBUG record per HTTP response, token requests
included, with the method, the path (without its query string, which can
hold Learner emails), the status, the latency and the request id. Request
and response bodies, headers and credentials are never logged, because
they hold Learner details. Nothing appears until you turn DEBUG on for the
logger:

<!-- sample: logging -->
```python
import logging

logging.basicConfig()
logging.getLogger("teachmehipaa").setLevel(logging.DEBUG)

client.learners.list()
# DEBUG:teachmehipaa:GET /v1/organizations/org_acme/learners 200 in 84 ms (request id req_7f3c2a)
```

Each record also carries the fields as attributes (`method`, `path`,
`status`, `latency_ms`, `request_id`) for structured log handlers.
