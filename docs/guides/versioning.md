# Versioning

## Semantic versioning

The library follows [semantic versioning](https://semver.org/). Within a
major version, upgrades don't break code that uses the public API: the
names exported from `teachmehipaa` and `teachmehipaa.types`, the clients'
resources and methods, and their documented behavior. Modules whose names
start with an underscore, such as `teachmehipaa._core`, are private and can
change in any release.

- **Patch** releases fix bugs.
- **Minor** releases add features, such as new methods, arguments, models,
  fields or Event types.
- **Major** releases may remove or rename something, or change behavior you
  rely on. The [changelog](../../CHANGELOG.md) lists every change.

The library is pre-release until 1.0.0 ships with the Developer API's
general availability; until then, names and behavior can still change.

`teachmehipaa.__version__` holds the installed version, and the client
sends it in its `User-Agent`.

## `OPENAPI_VERSION`

The resources and models are generated from the Developer API's OpenAPI
document. [`OPENAPI_VERSION`](../../OPENAPI_VERSION) in this repository
names the release of that document a version of the library was generated
from, and the changelog repeats it for each release. A newer release of the
API document reaches you as a new library release.

## Additive API changes

The Developer API changes additively: it adds endpoints, optional
arguments, response fields, enum values, error codes and Event types, and
doesn't remove or rename them. The library is built so those additions
don't break an older version of it:

- Models keep response fields they don't know, in `model_extra`, instead
  of failing to parse.
- Enum fields are open: they are typed as their known values or `str`, so a
  new value parses as a plain string.
- An Event of a type this version doesn't know arrives as `UnknownEvent`,
  and other unions have their own `Unknown*` fallback, such as
  `UnknownWebhookDeliveryResult`.
- Error `code`s are open strings, so a new code still raises the right
  error class for its HTTP status.

So handle the values you know and keep a fallback for the rest: an `else`
branch for enum values and Event types, and a catch-all for error codes.
Upgrade to use what the API added.

## Supported Python versions

Python 3.10 or newer. CI tests every release on Python 3.10 through 3.13.
