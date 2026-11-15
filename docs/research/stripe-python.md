# stripe-python: design research for `teachmehipaa-python`

- **Source:** `stripe/stripe-python` cloned shallow at commit
  `7254286570dcacb689f933db913e7cdf303818db` (2026-11-13). That is package
  **v17.0.0**, pinned API version `2026-10-28.endive`, `OPENAPI_VERSION`
  `v2596`. Local copy: `~/scratch/stripe-src/stripe-python`.
- **Citation format:** `path#Lx` links to
  `https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/<path>`.
- **Docs:** docs.stripe.com pages fetched 2026-11-15, cited inline.


---

## TL;DR

1. **Use the client style.** Build `StripeClient(api_key, ...)` and call namespaced services: `client.v1.customers.create(params, options)`. The legacy `stripe.api_key` + `stripe.Customer.create(...)` style still works. Stripe plans to deprecate it, and new endpoints may only ship on the client.
2. **Packaging:** flit_core, `requires-python >=3.9`. Runtime deps are only `requests` and `typing_extensions`. `httpx` comes with the `[async]` extra. Ships `py.typed`. CI checks types with pyright 1.1.336 (plus mypy on examples).
3. **About 97% of the code is generated** (1,601 of 1,651 `.py` files are marked "File generated from our OpenAPI spec"). The hand-written core is small: requestor, HTTP clients, errors, `StripeObject`, list objects, webhooks.
4. **Every method has a sync and an async twin** (`create` / `create_async`). Both share one request builder (`_args_for_request_with_retries`). They differ only in the HTTP transport call and the sleep call.
5. **Params are `TypedDict`s; responses are not.** Each endpoint gets a `TypedDict` for its params (`NotRequired` fields, open enums typed `Literal[...] | str`). Responses are `StripeObject` subclasses with attribute access. Since v15 these are not `dict`s; call `.to_dict()` for one.
6. **Per-request options** go in a separate `options=` `TypedDict`: `idempotency_key`, `stripe_account`, `stripe_version`, `api_key`, `max_network_retries`, `headers`.
7. **Retries:** off by default on `StripeClient`; on with 2 retries in the global style. Retried cases: connection errors, 409, 5xx, and `Stripe-Should-Retry: true`. Backoff is 0.5s × 2^n, capped at 5s, with jitter between 50% and 100%. There is **no `Retry-After` handling and no 429 retry**. An idempotency key is generated automatically for every POST and every v2 DELETE.
8. **Errors:** `StripeError` carries `http_status`, `code`, `request_id`, `headers`, `json_body` and `http_body`. The subclass is chosen from the status (v1) or from `error.type` (v2).
9. **Pagination:** `.auto_paging_iter()` returns an `AnyIterator` that supports both `for` and `async for`. v2 lists follow an opaque `next_page_url`, which is the model closest to our cursor pagination.
10. **Webhooks:** HMAC-SHA256 over `"{t}.{body}"`, header `t=…,v1=…`, default tolerance 300s, constant-time compare. Thin events use `parse_event_notification` and a typed `EventNotificationHandler`.

---

## 1. Repo layout, packaging, typing

**Layout** (repo root): `stripe/` (the package, 245 entries at the top level), `stripe/params/` (request `TypedDict`s), `stripe/v2/`, `stripe/events/`, `tests/`, `examples/`, `flake8_stripe/` (custom lint plugin), `deps/{build,dev,test}-requirements.txt`, `justfile`, `.hark/` (changelog fragments), `VERSION`, `OPENAPI_VERSION`, `CODEGEN_VERSION`.

Modules are private (`stripe/_customer.py`, `stripe/_customer_service.py`). The public surface is re-exported lazily from `stripe/__init__.py`: a generated `_import_map` plus a module-level `__getattr__`. Type checkers see the real symbols through a `TYPE_CHECKING` block ([`stripe/__init__.py#L581`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/__init__.py#L581), [`#L954`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/__init__.py#L954)). Sub-services also load lazily through `__getattr__` + `_subservices` ([`stripe/_payment_intent_service.py#L51-L79`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_payment_intent_service.py#L51-L79)). The HTTP library is still chosen at import time on purpose, so the import cost lands during Lambda init and not inside `StripeClient()` ([`stripe/_http_client.py#L1520-L1592`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_http_client.py#L1520-L1592)).

**Packaging** ([`pyproject.toml`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/pyproject.toml)):

```toml
[project]
name = "stripe"
requires-python = ">=3.9"
dependencies = ["typing_extensions >= 4.7.0", "requests >= 2.20"]
[project.optional-dependencies]
async = ["httpx"]
[build-system]
requires = ["flit_core >=3.11, <4"]
build-backend = "flit_core.buildapi"
```

The version string lives in three places: `VERSION`, `stripe/_version.py` and `pyproject.toml`. `just update-version` keeps them in sync with perl one-liners ([`justfile`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/justfile)). The classifiers still list Python 3.7 and 3.8, which is stale. The docs give the support policy as "We support *Python 3.9+*" with a 1-year extended window after EOL; 3.9 is deprecated and drops in March 2027 ([docs: SDK versioning](https://docs.stripe.com/sdks/versioning?lang=python)).

**Typing:**

- `stripe/py.typed` is present.
- Request params are `TypedDict` classes in `stripe/params/` (e.g. [`stripe/params/_payment_intent_cancel_params.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/params/_payment_intent_cancel_params.py)). v1 param dicts **inherit `RequestOptions`**, which lets the legacy `**kwargs` style mix params and options. v2 param dicts do not ([`stripe/params/v2/core/_event_list_params.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/params/v2/core/_event_list_params.py)).
- Pyright runs on `stripe/` plus selected tests with `reportUnnecessaryTypeIgnoreComment` and similar settings. mypy runs only on `tests/test_generated_examples.py` and `tests/test_exports.py` ([`pyproject.toml`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/pyproject.toml)).
- Pyright is pinned to `1.1.336` because newer versions flag override issues ([`deps/dev-requirements.txt`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/deps/dev-requirements.txt)).
- Open enums are typed `Union[Literal[...], str]`.
- The README states that **type changes ship in minor releases** and are outside semver ([`README.md`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/README.md), "Types and the Versioning Policy").

```python
class PaymentIntentCancelParams(RequestOptions):
    cancellation_reason: NotRequired[
        "Literal['abandoned', 'duplicate', 'fraudulent', 'requested_by_customer']|str"
    ]
    expand: NotRequired[List[str]]
```

## 2. Two usage styles

**Legacy global style.** Module globals (`stripe.api_key`, `stripe.max_network_retries = 2`, `stripe.proxy`, `stripe.default_http_client`, ...) and classmethods on resource classes ([`stripe/__init__.py#L26-L44`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/__init__.py#L26-L44)). Resource classes mix in `CreateableAPIResource`, `ListableAPIResource`, and so on ([`stripe/_customer.py#L121`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_customer.py#L121)). Custom methods work both as a classmethod and on an instance through `@class_method_variant("_cls_cancel")` ([`stripe/_payment_intent.py#L3764-L3833`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_payment_intent.py#L3764-L3833)).

```python
stripe.api_key = "sk_test_..."
stripe.Customer.create(email="a@b.com", idempotency_key="k1")  # params+options in **kwargs
pi.cancel()  /  stripe.PaymentIntent.cancel("pi_123")
```

**Client style.** `StripeClient` holds one `_APIRequestor` with immutable `RequestorOptions` and exposes `client.v1`, `client.v2` and `client.oauth` ([`stripe/_stripe_client.py#L149-L226`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_stripe_client.py#L149-L226)). Services are thin generated classes over `StripeService._request` ([`stripe/_stripe_service.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_stripe_service.py)).

```python
client = StripeClient("sk_test_...")
client.v1.customers.create({"email": "a@b.com"}, {"idempotency_key": "k1"})
client.v1.payment_intents.cancel("pi_123")              # path param positional-only
client.v2.core.accounts.close("acct_123")
```

**Recommendation:** the README section "StripeClient vs legacy pattern" says the legacy pattern "will be marked as deprecated soon" and "Once the legacy pattern is deprecated, new API endpoints will only be accessible in the StripeClient" ([`README.md`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/README.md)). Every example on docs.stripe.com now uses `client.v1.*` ([docs: error handling](https://docs.stripe.com/error-handling?lang=python)). The global style has real costs: process-wide mutable state, mixing params and options in `**kwargs`, and the global HTTP client warning when you change `stripe.proxy` after the first request ([`stripe/__init__.py#L73-L84`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/__init__.py#L73-L84)). In v16, path params became **positional-only** (`intent: str, /`) so spec-derived names stop being public API (CHANGELOG 16.0.0, #1920).

## 3. Client config options and defaults

`StripeClient.__init__` keyword-only args ([`stripe/_stripe_client.py#L149-L226`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_stripe_client.py#L149-L226)):

| Option | Default | Notes |
|---|---|---|
| `api_key` (positional) | required | Raises `AuthenticationError` if `None` |
| `stripe_account`, `stripe_context` | None | Become `Stripe-Account` / `Stripe-Context` headers |
| `stripe_version` | `_ApiVersion.CURRENT` = `"2026-10-28.endive"` | [`stripe/_api_version.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_api_version.py) |
| `base_addresses` | `{"api": "https://api.stripe.com", "connect": ..., "files": "https://files.stripe.com", "meter_events": ...}` | `BaseAddresses` is a `TypedDict`; each service method names one with `base_address="files"` etc. ([`stripe/_base_address.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_base_address.py)) |
| `max_network_retries` | `None`, which means **0** on the client | The global default is 2 ([`stripe/__init__.py#L39`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/__init__.py#L39)). `_should_retry` treats `None` as 0 ([`stripe/_http_client.py#L117-L128`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_http_client.py#L117-L128)) |
| `proxy`, `verify_ssl_certs` | None / True | Cannot be combined with `http_client`; the constructor raises `ValueError` |
| `http_client` | auto: urlfetch > requests > pycurl > urllib (sync); httpx+anyio > aiohttp (async) | [`stripe/_http_client.py#L1545-L1592`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_http_client.py#L1545-L1592) |
| `client_id` | None | For OAuth (Connect) |

Points to note:

- **There is no `timeout` on `StripeClient`.** Timeouts belong to the HTTP client: `RequestsClient(timeout=80)` default ([`#L512`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_http_client.py#L512)), and `HTTPXClient` / `AIOHTTPClient` also default to 80.
- **Telemetry** is a global switch (`stripe.enable_telemetry = True`).
- The client has **no `close()` and no context manager**. Lifecycle stays with the injected `HTTPClient.close()` / `close_async()`.
- `with_stripe_context()` returns a new client that reuses the same `HTTPClient`, keeping TLS connections warm ([`#L345`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_stripe_client.py#L345)). This is the immutable copy-with pattern.
- TLS uses a bundled CA file (`stripe/data/ca-certificates.crt`) by default.

## 4. Sync vs async

- **Naming:** every request method has an `*_async` twin: `retrieve_async`, `list_async`, `cancel_async`, `raw_request_async` ([`stripe/_payment_intent_service.py#L377-L429`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_payment_intent_service.py#L377-L429)). A custom flake8 rule, `ASY = flake8_stripe:AsyncNamingConventions`, enforces it ([`.flake8`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/.flake8)).
- **Shared code:**
  - `_APIRequestor._args_for_request_with_retries` builds the URL, headers and body once for both paths ([`stripe/_api_requestor.py#L688-L838`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_api_requestor.py#L688-L838)).
  - `HTTPClient` has parallel `_request_with_retries_internal` and `_request_with_retries_internal_async` loops built on the same `_should_retry` and `_sleep_time_seconds`. The only differences are `time.sleep` vs `await self.sleep_async` (anyio or asyncio) ([`stripe/_http_client.py#L253-L468`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_http_client.py#L253-L468)).
  - Response interpretation (`_interpret_response`) is shared.
- **One client object for both:** a sync `HTTPClient` carries an `async_fallback_client`. The default `RequestsClient` hands async calls to `HTTPXClient`, so the same `StripeClient` serves both ([`stripe/_stripe_client.py#L196-L204`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_stripe_client.py#L196-L204)). `HTTPXClient(allow_sync_methods=False)` raises on sync use by default ([`#L1252-L1263`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_http_client.py#L1252-L1263)).
- **Generated twins:** the async bodies are copies of the sync bodies produced by codegen. That is roughly double the generated code, but no code is shared through threads or `asyncio.run`.

## 5. Resource and service organization

- **Generated vs hand-written:** generated files start with `# File generated from our OpenAPI spec`. Generated blocks inside hand-written files sit between `The beginning/end of the section generated from our OpenAPI spec` markers ([`CONTRIBUTING.md`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/CONTRIBUTING.md)). Examples are the v2 error switch in [`stripe/_api_requestor.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_api_requestor.py) and the service list in `StripeClient`. The code generator is private; `CODEGEN_VERSION` records its git sha.
- **Service shape:** `client.v1.<resource_plural>.<verb>`. Sub-resources nest (`client.v1.payment_intents.amount_details_line_items`), and so do v2 namespaces (`client.v2.core.accounts`).
  - Verbs: `list`, `create`, `retrieve`, `update` (service) / `modify` (legacy class), `delete`, `search`, plus **custom methods named after the path suffix**: `cancel`, `capture`, `confirm`, `close`, `pdf`.
  - Signature: `(path_params..., /, params: Optional[XParams]=None, options: Optional[RequestOptions]=None) -> Resource`.
  - Path params are escaped with `sanitize_id` = `urllib.parse.quote_plus` ([`stripe/_util.py#L362`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_util.py#L362)).
  - `validate_path` rejects non-origin-relative paths, because some URLs come from untrusted webhook bodies ([`#L367`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_util.py#L367)).
- **Response objects:** `StripeObject` is "**not** a `dict` even though `str()` on one prints JSON". The goal is that API fields like `items` never collide with dict methods ([`stripe/_stripe_object.py#L97-L108`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_stripe_object.py#L97-L108)).
  - Access: attribute, `obj["k"]`, `"k" in obj`, and `.to_dict(recursive=, for_json=)`.
  - `.last_response` gives `code`, `headers`, `request_id` and `idempotency_key` ([`stripe/_stripe_response.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_stripe_response.py)).
  - Nested types are inner classes (e.g. `Customer.Address`), resolved through `_get_inner_class_type` and `_get_union_variant_class` (discriminated unions).
  - v17 strips the API key from pickles; call `reattach_api_key()` after unpickling ([`#L343`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_stripe_object.py#L343)).
- **v1/v2 namespaces:** `V1Services` and `V2Services` ([`stripe/_v2_services.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_v2_services.py)). `get_api_mode(url)` picks the encoding and error mapping: v1 sends form-encoded bodies, v2 sends JSON ([`stripe/_api_requestor.py#L676-L681`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_api_requestor.py#L676-L681); [docs: API v2 overview](https://docs.stripe.com/api-v2-overview)).
- **Numeric fields:** `decimal_string` fields became `decimal.Decimal` in v15, and v2 `int64_string` fields are coerced to `int` (`_coerce_v2_params`, CHANGELOG 15.0.0).

## 6. Per-request options

`RequestOptions` is a `TypedDict` ([`stripe/_request_options.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_request_options.py)):

```python
class RequestOptions(TypedDict):
    api_key: NotRequired["str|None"]
    stripe_version: NotRequired["str|None"]
    stripe_account: NotRequired["str|None"]
    stripe_context: NotRequired["str | StripeContext | None"]
    max_network_retries: NotRequired["int|None"]
    idempotency_key: NotRequired["str|None"]
    content_type: NotRequired["str|None"]
    headers: NotRequired["Mapping[str, str]|None"]
```

- `merge_options(requestor, request)` lets per-request values win over client values. `idempotency_key`, `content_type` and `headers` exist only per request.
- Extra `headers` are applied last and can override computed headers ([`stripe/_api_requestor.py#L818-L820`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_api_requestor.py#L818-L820)).
- Usage: `client.v1.customers.list(options={"stripe_account": "acct_...", "stripe_version": "2019-02-19"})` ([`README.md`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/README.md) "Per-request Configuration").

## 7. Pagination

**v1 `ListObject[T]`** ([`stripe/_list_object.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_list_object.py)):

- Fields: `data`, `has_more`, `url`. It is iterable over the current page.
- `auto_paging_iter()` follows `starting_after=<last id>`, or `ending_before` when the first request used it, iterating in reverse.
- `next_page()` and `previous_page()` return an empty list when `has_more` is false.
- The original filters live in `_retrieve_params` and are replayed on each page.

**`AnyIterator`** takes one sync and one async generator and supports both `for` and `async for`. It raises if you mix the two ([`stripe/_any_iterator.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_any_iterator.py)).

```python
for c in client.v1.customers.list({"limit": 100}).auto_paging_iter(): ...
async for c in (await client.v1.customers.list_async()).auto_paging_iter(): ...
```

**Search** (`SearchResultObject`) uses an opaque `next_page` token sent back as `page` ([`stripe/_search_result_object.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_search_result_object.py)). v2 search (16.1.0) sends `limit` in the query string and the body as JSON ([`stripe/_stripe_service.py#L16-L26`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_stripe_service.py#L16-L26)).

**v2 `ListObject`** follows the server-provided `next_page_url` until it is `null` ([`stripe/v2/_list_object.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/v2/_list_object.py)). Per the docs, "You can't change list filters after the first request" ([docs: API v2 overview](https://docs.stripe.com/api-v2-overview#list-pagination)). **This model is the closest match to our cursor pagination.**

## 8. Errors

Hierarchy ([`stripe/_error.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_error.py)):

- `StripeError(Exception)`
  - `APIError`
  - `APIConnectionError` (`should_retry: bool`)
  - `StripeErrorWithParamCode`
    - `CardError` (402, `.param`)
    - `InvalidRequestError` (400/404, `.param`)
  - `IdempotencyError`
  - `AuthenticationError` (401)
  - `PermissionError` (403)
  - `RateLimitError` (429)
  - `SignatureVerificationError` (`.sig_header`)
  - Generated v2 types keyed on `error.type`: `AlreadyCanceledError`, `NotCancelableError`, `QuotaExceededError`, `CannotProceedError(reason=)`, and others
- OAuth errors live separately in `stripe/oauth_error.py`.

Fields on `StripeError`:

- `http_body`, `http_status`, `json_body`, `headers`, `code`
- `request_id`, taken from the `request-id` header ([`#L55`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_error.py#L55))
- `error`, a parsed `ErrorObject`
- `user_message`, the raw message
- `__str__` returns `"Request {req_id}: {msg}"`

Errors pickle cleanly since 16.1.0.

Mapping ([`stripe/_api_requestor.py#L378-L606`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_api_requestor.py#L378-L606)):

1. A body with no `error` key raises `APIError("Invalid response object…")`.
2. If `error` is a string, the OAuth mapping applies.
3. For v2, the error class comes from `error.type`, falling back to the v1 mapping.
4. For v1, the error class comes from the status: 429 (or 400 with `code=rate_limit`) maps to `RateLimitError`. 400/404 map to `IdempotencyError` when `type=idempotency_error`, otherwise `InvalidRequestError`. 401 maps to `AuthenticationError`, 402 to `CardError`, 403 to `PermissionError`, and anything else to `APIError`.

Stripe's error envelope is `{"error": {"type","code","message","param","doc_url","request_log_url"}}` ([docs: error handling](https://docs.stripe.com/error-handling?lang=python)).

## 9. Retries

From [`stripe/_http_client.py#L86-L186`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_http_client.py#L86-L186).

- **Count:** `max_network_retries` (client default 0, global default 2). Can be overridden per request.
- **Retried:**
  - Connection errors where the transport set `should_retry=True`: timeouts and connection errors only, never SSL errors ([`#L640-L691`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_http_client.py#L640-L691)).
  - `Stripe-Should-Retry: true`. A `false` value vetoes the retry.
  - **409**.
  - **>= 500**.
- **Not retried:** 429 gets no special case and is not retried. **`Retry-After` is not read anywhere** (`grep -ri retry-after stripe/` finds nothing).
- **Backoff:** `sleep = min(0.5 * 2**(n-1), 5)`, then jitter `sleep *= 0.5 * (1 + uniform(0,1))`, then a floor at `max(0.5, sleep)`. Constants: `INITIAL_DELAY = 0.5`, `MAX_DELAY = 5`.
- **Automatic idempotency keys:** `headers.setdefault("Idempotency-Key", _generate_idempotency_key())` for every POST and every v2 DELETE. The key is a UUID-shaped value built from `os.urandom(16)` ([`stripe/_api_requestor.py#L108-L110`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_api_requestor.py#L108-L110), [`#L672-L674`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_api_requestor.py#L672-L674)). It is generated once, before the retry loop, so every retry reuses it.
- **Server-side semantics:** v1 keys are kept at least 24h and must be at most 255 chars; a replay returns the cached response. v2 replays re-execute failed work within 30 days ([docs: idempotent requests](https://docs.stripe.com/api/idempotent_requests), [docs: API v2 overview](https://docs.stripe.com/api-v2-overview#idempotency)). The docs say "Stripe SDKs respect this header automatically" about `Stripe-Should-Retry` ([docs: advanced error handling](https://docs.stripe.com/error-low-level)).

## 10. HTTP layer, logging, telemetry, User-Agent

**HTTP abstraction.** `HTTPClient` base class ([`stripe/_http_client.py#L75`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_http_client.py#L75)):

- Subclasses implement `request`, `request_stream`, `close` and their async forms. Each returns `(body, status, headers)` and raises `APIConnectionError(should_retry=...)` on transport failures.
- Built-in clients: `RequestsClient` (thread-local `Session`), `UrllibClient`, `PycurlClient`, `UrlFetchClient`, `HTTPXClient`, `AIOHTTPClient`.
- Users can subclass it ([`README.md`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/README.md) "Async").

**Logging** ([`stripe/_util.py#L34-L65`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_util.py#L34-L65)):

- Logger name `"stripe"`, logfmt messages.
- `STRIPE_LOG=debug|info` or `stripe.log = "debug"` also prints to stderr.
- Info level logs request method/URL, response code, error summaries and retry notices. Debug level adds the POST body and the response body, so **debug logs payloads**.

**Headers** ([`stripe/_api_requestor.py#L614-L686`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_api_requestor.py#L614-L686)):

- `User-Agent: Stripe/v1 PythonBindings/17.0.0`, plus ` {AppName}/{version} ({url})` when `set_app_info` was called, plus ` AIAgent/<name>` when env vars like `CLAUDECODE` or `CURSOR_AGENT` are set.
- `X-Stripe-Client-User-Agent`: JSON with `bindings_version`, `lang`, `lang_version`, `httplib`, `platform` (only with telemetry on), `application` and `telemetry_id`.
- `Authorization: Bearer <key>`, `Stripe-Version`, `Stripe-Account`, `Stripe-Context`, `Idempotency-Key`, `Content-Type`.

**Telemetry:**

- `X-Stripe-Client-Telemetry: {"last_request_metrics": {"request_id","request_duration_ms","usage"}}` is sent on the *next* request, stored per thread ([`stripe/_http_client.py#L189-L211`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_http_client.py#L189-L211), [`stripe/_request_metrics.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_request_metrics.py)).
- A persistent random `telemetry_id` is written to `~/.config/stripe/telemetry_id` ([`stripe/_telemetry_id.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_telemetry_id.py)).
- Turn it off with `stripe.enable_telemetry = False`.

**`set_app_info(name, partner_id=, url=, version=)`** sets a global ([`stripe/__init__.py#L95`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/__init__.py#L95)). It is intended for plugin authors.

**Other behavior:**

- `Stripe-Notice` response headers are surfaced through `warnings.warn` and can be suppressed with `STRIPE_SUPPRESS_NOTICES` ([`#L77-L101`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_api_requestor.py#L77-L101)).
- **Importing `stripe` writes a `<claude-code-hint>` line to stderr when `CLAUDECODE` is set** ([`stripe/_util.py#L441-L454`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_util.py#L441-L454)). This is an import-time side effect we should not copy.

## 11. Webhooks

From [`stripe/_webhook.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_webhook.py).

**Verification:**

- `Webhook.DEFAULT_TOLERANCE = 300` and `WebhookSignature.EXPECTED_SCHEME = "v1"`.
- `verify_header(payload, header, secret, tolerance)`:
  1. Decodes bytes to str.
  2. Rejects a missing header, or a secret that is missing or only whitespace.
  3. Parses `t` and every `v1`.
  4. Computes `HMAC-SHA256(secret, f"{t}.{payload}")` as hex.
  5. Checks it against any `v1` value with `hmac.compare_digest`.
  6. Rejects when `timestamp < now - tolerance`. Only the past is checked; future timestamps pass. A tolerance of 0 or `None` disables the check ([`#L141-L199`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_webhook.py#L141-L199)).
- v17 adds diagnostic messages that use the unsigned `secret` / `payload` debug entries to point at a wrong secret or a modified body.
- `generate_signature_header(payload, secret, timestamp=None)` builds headers for tests ([`#L129`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_webhook.py#L129)).

**Snapshot events:** `Webhook.construct_event(payload, sig_header, secret, tolerance)` or `client.construct_event(...)` verifies and returns a typed `Event`. `construct_event_without_verification` also unwraps AWS EventBridge and Azure Event Grid envelopes ([`#L44-L69`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_webhook.py#L44-L69)).

**Thin events (v2):**

- `client.parse_event_notification(raw, sig_header, secret)` returns a typed `EventNotification` subclass, picked by `type`. Unknown types become `UnknownEventNotification`.
- Each notification has `fetch_event()` and `fetch_related_object()`, which call back to the API through a client bound to the event's `context` ([`stripe/v2/core/_event.py#L142-L256`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/v2/core/_event.py#L142-L256)).
- `client.notification_handler(secret, fallback)` returns a handler with generated `@handler.on_<event_type>` decorators, `pre_handle` (for dedup) and `handle(body, sig)`, in sync and async variants ([`stripe/_event_notification_handler.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_event_notification_handler.py)).

**What the docs add** ([docs: webhooks verify-manually](https://docs.stripe.com/webhooks#verify-events)):

- "Our libraries have a default tolerance of 5 minutes."
- "Don't use a tolerance value of `0`."
- "ignore signature schemes other than `v1`" to prevent downgrade attacks.
- Multiple `v1` signatures appear while a secret is rolled (up to 7 days).
- Integrations "must accept unknown entries and must not depend on a fixed entry count or order."

## 12. Raw requests, uploads, binary downloads

**Raw requests:** `client.raw_request(method, path, **params)` and `raw_request_async`. Options are pulled out of the kwargs (`stripe_version=`, `headers=`, ...), along with `base=`. The call returns a `StripeResponse`; `client.deserialize(resp, api_mode="V1")` turns it into a `StripeObject` ([`stripe/_stripe_client.py#L285-L343`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_stripe_client.py#L285-L343)).

**Multipart upload:** `FileService.create` sets `options["content_type"] = "multipart/form-data"` and `base_address="files"` ([`stripe/_file_service.py#L56-L78`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_file_service.py#L56-L78)). The requestor then switches to a hand-rolled `MultipartDataGenerator` ([`stripe/_api_requestor.py#L802-L811`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_api_requestor.py#L802-L811), [`stripe/_multipart_data_generator.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_multipart_data_generator.py)).

**Binary download:** `QuoteService.pdf(quote)` calls `_request_stream` against the `files` base ([`stripe/_quote_service.py#L347-L366`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_quote_service.py#L347-L366)).

- Sync returns `StripeStreamResponse(io, code, headers)`, where `io` is the raw stream (`requests`' `result.raw`).
- Async returns `StripeStreamResponseAsync` with `.stream()` and `await .read_async()` ([`stripe/_stripe_response.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_stripe_response.py)).
- On a non-2xx status the stream is read and parsed as a JSON error ([`stripe/_api_requestor.py#L1033-L1079`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/stripe/_api_requestor.py#L1033-L1079)).
- **Weakness:** the generated return type is `"Any"`.

## 13. Testing, lint, CI, release, codegen, README

**Testing:**

- pytest with `-n auto` (xdist), pytest-mock and anyio (asyncio + trio).
- Most tests run against **stripe-mock**, a Go server fed the OpenAPI spec and fixtures. `conftest.py` exits if it is unreachable, unless `--nomock` is passed ([`tests/conftest.py`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/tests/conftest.py)).
- CI starts stripe-mock pinned to `OPENAPI_VERSION`, and a canary workflow runs against the latest specs ([`.github/actions/test/action.yml`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/.github/actions/test/action.yml)).
- `tests/http_client_mock.py` wraps the HTTP client with `assert_requested(method, path, query_string, post_data, extra_headers, usage, ...)`.
- `tests/test_integration.py` spins up a real `BaseHTTPRequestHandler` server for proxy and telemetry tests.
- `tests/test_generated_examples.py` is codegen output and is also type-checked.

**Lint and format:**

- `ruff format` with line-length 79 (Black-compatible; ruff is used *only* as the formatter).
- `flake8` + `flake8-bugbear` (B006 only) + the custom `flake8_stripe` plugin: typing imports, no `import stripe` inside the package, no new public modules, async naming ([`.flake8`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/.flake8)).
- pyright for types and mypy for examples. The task runner is `just` ([`justfile`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/justfile)).

**CI** ([`.github/workflows/ci.yml`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/.github/workflows/ci.yml)):

- Jobs: lint, build (`python -m build` + `twine check`), and a test matrix over 3.9–3.14, PyPy 3.9–3.11 and Windows 3.14.
- Actions are SHA-pinned and `zizmor` audits the workflows.

**Release:**

- A tag push `v*` triggers the `publish` job in environment `publish` with `id-token: write`, using `pypa/gh-action-pypi-publish` with **no token**. That is **PyPI Trusted Publishing (OIDC)**.
- The dist artifact from the `build` job is downloaded with digest checking.
- Preview channels use `bN` (public preview) and `aN` (private preview) version suffixes ([`README.md`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/README.md)).

**Changelog:** `CHANGELOG.md` is generated by `hark build` from `.hark/changes/*.change.md` fragments ([`CHANGELOG.md#L1-L4`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/CHANGELOG.md#L1-L4)). Breaking items are marked ⚠️ and link migration guides in the wiki.

**Codegen:**

- `OPENAPI_VERSION` (`v2596`) pins the spec, and `CODEGEN_VERSION` pins the private generator sha.
- Generated output covers services, resource classes, params `TypedDict`s, event classes, the v2 error switch, `_api_version.py`, the AI-agent table and the `__init__` import map.
- Hand-written code covers the requestor, HTTP clients, `StripeObject`, list/search objects, webhooks, the OAuth service and `StripeContext`.

**README structure:**

1. Install / Requirements
2. Usage (client example)
3. Working with API resources (not-a-dict table)
4. StripeClient vs legacy
5. Exceptions
6. Per-request config
7. HTTP client
8. Proxy
9. Retries
10. Logging
11. Notices
12. `last_response`
13. Undocumented params
14. Plugins (`set_app_info`)
15. Telemetry
16. Types (versioning policy, API versions, open/closed enums)
17. Preview SDKs
18. Custom requests
19. Async
20. Support
21. Development

([`README.md`](https://github.com/stripe/stripe-python/blob/7254286570dcacb689f933db913e7cdf303818db/README.md))

---

## Adopt / Adapt / Skip for teachmehipaa-python

| # | Stripe pattern | Verdict | What we do |
|---|---|---|---|
| 1 | `StripeClient` instance + `client.v1.<svc>` services | **Adopt** | `TeachMeHIPAA(client_id=..., client_secret=..., environment="sandbox")` exposing `client.organizations.enrollments.cancel(org_id, id)`. We have one API version, so no `v1` namespace; keep it as a slot only if a `/v2` ever lands. |
| 2 | Legacy global `stripe.api_key` + `Resource.create` classmethods | **Skip** | Stripe is deprecating it. With token caching it would mean global mutable auth state. No module globals. |
| 3 | Static secret key in `Authorization: Bearer` | **Adapt** | An `Auth` strategy: (a) `ClientCredentials`: POST the token endpoint, cache the 15-min JWT in memory, refresh proactively about 60s before `exp`, refresh once on 401 and replay, guard concurrent refresh with a lock (sync) / `asyncio.Lock` (async); there is no refresh token, so just request a new one. (b) `AuthorizationCodePKCE`: a helper for `authorize_url` + `code_verifier`, plus `RefreshTokenAuth` with **rotation** (persist the new refresh token through an `on_token_refresh` callback or a `TokenStore` protocol). (c) `StaticToken` for tests. |
| 4 | `base_addresses` dict (`api`/`files`/`connect`) | **Adapt** | `environment: Literal["live","sandbox"]` maps to the base URLs, with a `base_url=` override. A single base unless the PDF is served from another host. |
| 5 | `max_network_retries` default 0 on the client | **Adapt** | Default to **2**: retries are only safe because we always send an Idempotency-Key. |
| 6 | Retry 409 / 5xx / conn errors, `Stripe-Should-Retry`, 0.5s→5s backoff with jitter | **Adapt** | Keep the backoff constants and jitter. **Add 429 and honor `Retry-After`** (seconds or HTTP-date, capped), which Stripe does not do. Only retry 409 if our API defines it as "concurrent request with the same key". Never retry non-idempotent requests that have no key. |
| 7 | Automatic `Idempotency-Key` on every POST (and v2 DELETE), generated once before the retry loop | **Adopt** | Same, using `uuid4()`. Also apply it to AIP-136 `:cancel`-style POSTs. Expose `idempotency_key=` per request. Return `Idempotent-Replayed` on the response metadata if our API sends it. |
| 8 | `options=` `RequestOptions` `TypedDict` per call | **Adopt** | `RequestOptions(idempotency_key, timeout, max_retries, extra_headers, if_match)`. Prefer explicit keyword-only args, e.g. `cancel(org_id, id, /, *, request_options=None)`. |
| 9 | Params as `TypedDict`s, open enums `Literal[...] \| str` | **Adopt** | Generate from OpenAPI 3.1. Keep open enums as `Literal \| str` so new server values don't break parsing. |
| 10 | `StripeObject` dynamic attribute objects | **Adapt** | Use generated **frozen dataclasses or pydantic v2 models** (typed responses) with `.to_dict()`, `extra="allow"` for forward compatibility, and a `.response` metadata attribute (status, headers, request_id, etag). Pick one; dynamic objects lose typing. |
| 11 | ETag | **Add** (Stripe has none) | Expose `etag` on the model or response. `update(..., if_match=etag)` sends `If-Match`, and a 412 raises `PreconditionFailedError`. Optionally `If-None-Match` on GET returns `NotModified`. |
| 12 | v1 `ListObject` (`starting_after` = last id) | **Skip** | |
| 13 | v2 `ListObject` (`next_page_url`) + `AnyIterator` | **Adopt** | Have `Page[T]` with `data`, `next_cursor` and `has_next_page()`. Return `SyncPager[T]` from `list()` and `AsyncPager[T]` from `list_async()` (separate types: clearer than `AnyIterator`, which fails at runtime if you mix sync and async). Freeze filters across pages, as Stripe v2 does. |
| 14 | Error envelope `{"error":{type,code,message,param}}` → status-mapped subclasses | **Adapt** | Parse **RFC 9457 `application/problem+json`**: `type`, `title`, `status`, `detail`, `instance`, plus extensions (`errors[]` for field validation, `code`). Base `TeachMeHIPAAError(message)`; `APIStatusError` with `status`, `problem` (typed), `request_id`, `headers`, `body`. Subclasses by status: `BadRequest` (400), `Authentication` (401), `PermissionDenied` (403), `NotFound` (404), `Conflict` (409), `PreconditionFailed` (412), `UnprocessableEntity` (422), `RateLimit` (429, with `retry_after`), `InternalServer` (5xx). Optional refinement by problem `type` URI, like Stripe's v2 `error.type` switch. `APIConnectionError` and `APITimeoutError` for transport failures. Fall back gracefully on non-problem bodies. |
| 15 | `request_id` from the `Request-Id` header, shown in `__str__` | **Adopt** | Use whatever request-id header our API emits (or `instance` from the problem). Include it in `__str__` and `__repr__`. |
| 16 | Sync + `*_async` twins on one client, shared request builder | **Adapt** | Ship **two classes**: `TeachMeHIPAA` (httpx.Client) and `AsyncTeachMeHIPAA` (httpx.AsyncClient). Share all request-building, retry-decision and parsing code as pure functions; only send and sleep differ, as in Stripe's split. Avoids `_async` name doubling and the fallback-client trick. |
| 17 | Pluggable `HTTPClient` cascade (requests / urllib / pycurl / urlfetch / httpx / aiohttp) | **Skip** (cascade) / **Adopt** (injection) | Depend on **httpx only**: one transport for sync and async, with timeouts and proxies built in. Allow `http_client=httpx.Client(...)` injection for proxies, mTLS and test transports (`httpx.MockTransport`). |
| 18 | Timeout only on the HTTP client (80s default) | **Adapt** | Put `timeout` on the client (and per request), default `httpx.Timeout(60, connect=5)`. |
| 19 | No `close()` / context manager on the client | **Fix** | Add `close()`, `__enter__`/`__exit__`, `aclose()` and `__aenter__`/`__aexit__`. |
| 20 | `with_stripe_context()` copy sharing the HTTP pool | **Adopt** | `client.with_options(timeout=..., max_retries=...)` returns a copy that shares the transport and token cache. |
| 21 | Custom methods named after the path suffix (`cancel`, `close`) with positional-only path params | **Adopt** | AIP-136 `POST /organizations/{orgId}/enrollments/{id}:cancel` becomes `client.organizations.enrollments.cancel(org_id, id, /, ...)`. **Caution:** Stripe escapes ids with `quote_plus`, which would turn `:` into `%3A`. Build the template as `f"/organizations/{q(org_id)}/enrollments/{q(id)}:cancel"` with `q = partial(quote, safe="")`, so only ids are escaped and the `:verb` stays literal. Keep a `validate_path` guard. |
| 22 | (No LRO in Stripe) | **Add** | AIP-151: methods return `Operation[T]` with `name`, `done`, `metadata`, `error` (problem), `.refresh()`, `.wait(timeout=, poll_interval=)` / `await .wait_async()` (backoff and honor `Retry-After`) and `.result()`, which raises the mapped error. Also `client.operations.get(name)`. |
| 23 | Binary download via `_request_stream` returning `Any` / raw `io` | **Adapt** | `certificates.download_pdf(...) -> BinaryResponse` with `.content`, `.iter_bytes()`, `.write_to_file(path)`, `.content_type` and `.headers` (async: `aiter_bytes`). Typed, not `Any`. Parse non-2xx as problem+json, as Stripe does. |
| 24 | Multipart via a hand-rolled generator | **Skip** | Use httpx `files=` if we ever need uploads. |
| 25 | `raw_request` + `deserialize` escape hatch | **Adopt** | `client.request(method, path, json=, params=, cast_to=)` that keeps auth, retries and errors. |
| 26 | Webhook HMAC-SHA256 over `"{t}.{body}"`, header `t=,v1=`, tolerance 300, constant-time compare, test signer | **Adopt** (shape) | `teachmehipaa.webhooks.verify(payload: bytes, headers, secret, tolerance=300) -> Event` and `generate_test_header()`. **Improve:** also reject future timestamps beyond the tolerance, refuse `tolerance=0`, accept multiple `v1` values (secret rotation), ignore unknown entries, raise `WebhookVerificationError`. If our server signs differently (e.g. Standard Webhooks `webhook-id`/`webhook-timestamp`/`webhook-signature`), mirror the server exactly. |
| 27 | Typed event classes + `EventNotificationHandler` with `on_<type>` decorators | **Adapt (later)** | v1: return a discriminated-union `Event` parsed from the payload, plus `UnknownEvent`. The handler/decorator registry is optional sugar. |
| 28 | Logger `"stripe"`, `STRIPE_LOG` env, logfmt, debug logs bodies | **Adapt** | Logger `"teachmehipaa"`, `TEACHMEHIPAA_LOG=info\|debug`. **Never log bodies or bearer tokens**: this is a HIPAA product, so redact `Authorization`, tokens and PII fields even at debug. |
| 29 | `User-Agent: Stripe/v1 PythonBindings/x` + JSON `X-Stripe-Client-User-Agent` + `set_app_info` | **Adopt (lite)** | `User-Agent: teachmehipaa-python/{ver} python/{pyver} httpx/{ver}`, plus an `app_info=` **client option** (not a global). |
| 30 | Telemetry header with last-request metrics + persistent id in `~/.config` | **Skip** | Disk writes and implicit tracking don't suit compliance buyers. |
| 31 | Import-time side effects (Claude Code hint to stderr, AI-agent UA sniffing) | **Skip** | |
| 32 | `py.typed`, pyright on src, mypy on examples | **Adopt** | pyright strict plus mypy in CI. Tests import the public API only. |
| 33 | flit_core, deps `requests` + `typing_extensions`, `[async]` extra | **Adapt** | hatchling or flit_core; deps `httpx>=0.27`, `typing_extensions` (and pydantic if chosen). No extras needed, since httpx covers async. `requires-python >=3.10` (3.9 is EOL). |
| 34 | ruff format + flake8 + custom plugin | **Adapt** | ruff for both lint and format (one tool); add custom rules only if codegen needs them. |
| 35 | stripe-mock (spec-driven mock server) + `http_client_mock` | **Adapt** | `respx` or `httpx.MockTransport` for unit tests. Optional Prism (OpenAPI 3.1 mock) in CI, pinned to the spec version, as Stripe pins `OPENAPI_VERSION`. Contract tests against sandbox nightly. |
| 36 | CI matrix 3.9–3.14 + PyPy + Windows; SHA-pinned actions; zizmor | **Adopt** | Matrix 3.10–3.14 + Windows; SHA-pin; zizmor. |
| 37 | Tag → build → test → **PyPI Trusted Publishing** (OIDC, `environment: publish`) | **Adopt** | Same. |
| 38 | `OPENAPI_VERSION` / `CODEGEN_VERSION` files; generated-file headers and markers | **Adopt** | `OPENAPI_VERSION` holds the spec hash or tag. Add a "generated" header to every generated file and keep hand-written code outside generated dirs. |
| 39 | hark changelog fragments, ⚠️ breaking markers, wiki migration guides | **Adapt** | towncrier (or changesets-style fragments) with the same ⚠️ convention. |
| 40 | README sections list | **Adopt** | Same order, plus Auth (both flows), Pagination, LROs, ETags, Webhooks and PDF download. |
