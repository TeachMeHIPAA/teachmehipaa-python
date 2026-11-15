# httpx and pydantic, with separate sync and async clients

`teachmehipaa-python` depends on `httpx` and `pydantic` v2. Sync and async are
two classes, `TeachMeHipaa` and `AsyncTeachMeHipaa`, built on shared pure
request-building code. Stripe instead offers `*_async` twins of every method
over a fallback chain of six HTTP libraries. Pydantic is a heavy dependency,
but it gives typed, tolerant models (`extra="allow"`). Request params are
`TypedDict`s so callers can still pass plain dicts.
