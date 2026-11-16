# Authentication

An API client is a machine credential that belongs to exactly one
Organization in one Environment. The library turns its client id and
secret into short-lived Access tokens for you, and works out which
Organization they act for.

## Client credentials

Pass the API client's id and secret. Read them from the environment or a
secret manager; never commit them.

<!-- sample: client-credentials -->
```python
import os

from teachmehipaa import TeachMeHipaa

client = TeachMeHipaa(
    client_id=os.environ["TMH_CLIENT_ID"],
    client_secret=os.environ["TMH_CLIENT_SECRET"],
    environment="sandbox",
    scopes=["learners:read"],
)

token = client.auth.introspect()
print(token.mode, token.org_id, token.scopes)
```

The client exchanges the credentials for an Access token on the first call
that needs one, caches it and renews it 60 seconds before it expires.
Concurrent calls share one token request. If the API rejects a token
mid-flight (401), the client renews it once and replays the call; that
replay doesn't count as a retry. The secret is sent only to the token
endpoint, and the library never logs credentials or tokens.

`auth.introspect` describes the Access token: whether it belongs to an API
client, its Organization (`org_id`), its Scopes, its Environment (`mode`:
`"test"` in the Sandbox, `"live"` in Live) and when it expires. It needs no
Scope.

If the token endpoint refuses the credentials, the call raises
`OAuthError`, with the OAuth error in `code` (such as `invalid_client`).

## Scopes

A Scope is a named permission an Access token carries. An API client holds
the Scopes an admin granted it, and by default each Access token gets all
of them. Pass `scopes` to ask for fewer, as above, so a process that only
reads can't write.

| Scope               | Allows                                                           |
| ------------------- | ---------------------------------------------------------------- |
| `learners:read`     | Reading Learners                                                 |
| `learners:write`    | Creating, updating, offboarding and reminding Learners           |
| `enrollments:read`  | Reading Enrollments and the Seat inventory                       |
| `enrollments:write` | Creating, importing, cancelling, renewing and reminding Enrollments |
| `certificates:read` | Reading, exporting and downloading Certificates                  |
| `compliance:read`   | Reading the Compliance summary                                   |
| `members:read`      | Reading Members                                                  |
| `audit:read`        | Reading Audit events and the Event log                           |
| `webhooks:manage`   | Managing Webhook subscriptions and reading the Event log         |

The [resource reference](../reference/resources.md) lists the Scopes each
method needs. A call whose token lacks one raises `PermissionDeniedError`
(403).

## Environments

Every credential belongs to one Environment, and works only there.

| `environment`      | Base URL                                  | Use it for                                     |
| ------------------ | ----------------------------------------- | ---------------------------------------------- |
| `"live"` (default) | `https://api.tme.so/v1`                   | Your real Organization and Learners            |
| `"sandbox"`        | `https://sandbox.api.tme.so/v1` | Building and testing; no real Learners emailed |

`environment` defaults to `"live"`, so pass `environment="sandbox"` with
Sandbox credentials. Sandbox credentials sent to Live (or the other way
round) fail with `OAuthError`. To point the client at something else, such
as a mock server, pass `base_url`; it replaces the Environment's URL.

## The Organization binding

An API client belongs to one Organization, so you never pass an `org_id`.
On the first Organization-scoped call, the client asks `auth.introspect`
which Organization the token is for, once, and remembers the answer. If you
already know the id, pass it and the client skips that lookup:

<!-- sample: organization -->
```python
import os

from teachmehipaa import TeachMeHipaa

client = TeachMeHipaa(
    client_id=os.environ["TMH_CLIENT_ID"],
    client_secret=os.environ["TMH_CLIENT_SECRET"],
    organization_id="org_acme",
)

compliance = client.compliance.retrieve()
print(compliance.compliant_rate, compliance.last_response.request_id)
```

A client's configuration is fixed when you create it. To act for another
Organization, create another client with that Organization's credentials.

## Access tokens you already have

If something else gets Access tokens for you, pass a `token_provider`
instead of credentials. `StaticTokenProvider` sends one token as it is:

<!-- sample: static-token -->
```python
from teachmehipaa import StaticTokenProvider, TeachMeHipaa

client = TeachMeHipaa(
    token_provider=StaticTokenProvider(access_token),
    environment="sandbox",
)
print(client.compliance.retrieve().compliant_rate)
```

A static token is never renewed; once it expires, calls raise
`AuthenticationError`. On the async client, use `AsyncStaticTokenProvider`.

To fetch tokens your own way, pass any object with the `TokenProvider`
methods (`AsyncTokenProvider` on the async client): `access_token()`
returns a token to send, and `invalidate(access_token)` drops one the API
refused, so the next `access_token()` gets a fresh one. Pass either
`client_id` and `client_secret`, or `token_provider`, not both; `scopes`
belong to the token provider then.

## Public lookups without credentials

Three methods are public and send no Access token at all:
`courses.list`, `courses.retrieve` and `certificate_verifications.retrieve`.
To call only those, such as to check a Certificate someone showed you,
create a client without credentials:

<!-- sample: public-lookups -->
```python
from teachmehipaa import TeachMeHipaa

client = TeachMeHipaa(environment="sandbox")

verification = client.certificate_verifications.retrieve("aB3dE9")
print(verification.status, verification.learner_name)

for course in client.courses.list():
    print(course.title)
```

Any other method on such a client raises `ValueError` before it sends
anything. `AsyncTeachMeHipaa(environment="sandbox")` works the same way.
Certificate verification is limited to 60 requests a minute per IP
address.
