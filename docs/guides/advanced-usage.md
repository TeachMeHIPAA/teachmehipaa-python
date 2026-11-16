# Advanced usage

## Configure a client

You configure a client with keyword arguments to `TeachMeHipaa` (or
`AsyncTeachMeHipaa`), once, when you build it. The library keeps no global
state, so two differently configured clients can run side by side in one
process:

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

`environment`, `base_url` and `max_retries` read back as attributes, and
`timeout` reads back as an `httpx.Timeout`.

## Every client option

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

A client takes either `client_id` plus `client_secret` or a
`token_provider`; with a provider, `scopes` belongs to the provider. With
none of the three, it can only make the public calls (see
[Authentication](authentication.md#look-things-up-without-credentials)).
[Retries and timeouts](retries-and-timeouts.md) covers `max_retries` and
`timeout` in depth.

## Send requests through your own `httpx` client

Pass `http_client` to route requests through an `httpx.Client` you set up:
a corporate proxy, a custom CA bundle, client certificates for mTLS, or a
mock transport in tests (see [Testing](testing.md)). The library closes it
when you call `client.close()` or leave the `with` block. Give
`AsyncTeachMeHipaa` an `httpx.AsyncClient`.

## Identify your app in the User-Agent

`app_info` appends your software's name, and optionally its version and
URL, to the `User-Agent` header, after the library's own
`teachmehipaa-python/<version> python/<version> httpx/<version>`.
TeachMeHIPAA support uses it to find your traffic. The library sends no
telemetry beyond that header.

## Turn on debug logging

The library prints nothing and writes nothing to disk. It logs through the
standard `logging` module to the `teachmehipaa` logger: one DEBUG record per
HTTP response, token requests included, with the method, the path (minus the
query string, which can hold Learner emails), the status, the latency and
the request id. It never logs bodies, headers or credentials, since those
hold Learner details. You see nothing until you enable DEBUG for that
logger:

<!-- sample: logging -->
```python
import logging

logging.basicConfig()
logging.getLogger("teachmehipaa").setLevel(logging.DEBUG)

client.learners.list()
# DEBUG:teachmehipaa:GET /v1/organizations/org_acme/learners 200 in 84 ms (request id req_7f3c2a)
```

Each record also carries those values as attributes (`method`, `path`,
`status`, `latency_ms`, `request_id`) for a structured log handler to pick
up.
