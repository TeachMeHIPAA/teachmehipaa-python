# Versions and compatibility

## Python versions

`teachmehipaa` needs Python 3.10 or newer. CI runs the full test suite on
3.10, 3.11, 3.12 and 3.13, and type-checks the package with mypy in strict
mode. The package depends on `httpx` (0.27 up to, not including, 1.0),
`pydantic` 2.5 or newer within 2.x, and `typing-extensions` 4.7 or newer.

## How releases are numbered

Releases follow [semantic versioning](https://semver.org/). Within a major
version, an upgrade won't break code that sticks to the public API: the
names exported from `teachmehipaa` and `teachmehipaa.types`, the clients'
resources and methods, and the behavior these docs describe. Modules whose
names start with an underscore, such as `teachmehipaa._core`, are private
and can change in any release.

- A **patch** release fixes bugs.
- A **minor** release adds things: methods, arguments, models, fields,
  Event types.
- A **major** release may remove or rename something, or change behavior
  you depend on. The [changelog](../../CHANGELOG.md) lists every change.

Until 1.0.0 ships alongside the Developer API's general availability, treat
every release as pre-release: names and behavior can still move.
`teachmehipaa.__version__` holds the installed version, and the client
sends it in its `User-Agent`.

## Which API release you're on

The resources and models are generated from the Developer API's OpenAPI
document. [`OPENAPI_VERSION`](../../OPENAPI_VERSION) names the release of
that document this version of the library was built from, and the changelog
repeats it for each release. When the API document moves on, you get the
new surface by upgrading the library.

## Code that survives API additions

The Developer API grows by addition. It adds endpoints, optional arguments,
response fields, enum values, error codes and Event types, and it doesn't
remove or rename them. The library parses those additions without failing:

- Models keep response fields they don't declare, in `model_extra`.
- Enum-typed fields accept any string: each is typed as a `Literal` of the
  known values or `str`.
- An Event of an unknown type arrives as `UnknownEvent`, and other response
  unions fall back the same way, such as `UnknownWebhookDeliveryResult`.
- Error `code`s are plain strings, so a new code still raises the exception
  class for its HTTP status.

For your code, that means handling the values you know and giving the rest
a fallback: an `else` branch for enum values and Event types, and a default
branch when you dispatch on an error's `code`. Upgrade when you want to use
what the API added.
