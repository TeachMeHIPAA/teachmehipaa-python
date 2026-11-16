# Authentication

You authenticate as an API client: a machine credential that belongs to one
Organization in one Environment. Hand the client its id and secret, and it
handles the OAuth client-credentials exchange, the Access token's expiry and
the Organization lookup for you.

## Use your API client's credentials

Read the id and secret from the environment or your secret manager. Never
commit them.

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

Nothing goes over the wire until the first call that needs a token. Then
the client fetches one, caches it and fetches the next 60 seconds before it
expires. Concurrent calls wait on a single token request. When the API
answers 401 to a token it once accepted, the client fetches a new one and
replays the call once, and that replay doesn't use up a retry. Your secret
only ever travels to the token endpoint, and the library never logs it or
the token.

`auth.introspect()` tells you what your token is: an API client's or a
person's, which Organization it acts for (`org_id`), its Scopes, its
Environment (`mode` is `"test"` in the Sandbox and `"live"` in Live) and its
expiry. It needs no Scope.

A refused exchange raises `OAuthError`, with the OAuth error string in
`code`, such as `invalid_client`.

## Ask for fewer Scopes

A Scope is one permission an Access token carries. An admin grants Scopes to
the API client, and by default every token gets all of them. Pass `scopes`
to narrow the token, as the sample above does, so a reporting job that only
reads can't write.

| Scope               | Lets you                                                     |
| ------------------- | ------------------------------------------------------------ |
| `learners:read`     | Read Learners                                                |
| `learners:write`    | Create, update, offboard and remind Learners                 |
| `enrollments:read`  | Read Enrollments and the Seat inventory                      |
| `enrollments:write` | Create, import, cancel, renew and remind Enrollments         |
| `certificates:read` | Read, export and download Certificates                       |
| `compliance:read`   | Read the Compliance summary                                  |
| `members:read`      | Read Members                                                 |
| `audit:read`        | Read Audit events and the Event log                          |
| `webhooks:manage`   | Manage Webhook subscriptions and read the Event log          |

The [resource reference](../reference/resources.md) names the Scopes each
method needs. Call one without them and you get `PermissionDeniedError`
(403).

## Pick an Environment

Credentials work in their own Environment only.

| `environment`      | Base URL                                  | Use it for                                     |
| ------------------ | ----------------------------------------- | ---------------------------------------------- |
| `"live"` (default) | `https://api.tme.so/v1`                   | Your real Organization and Learners            |
| `"sandbox"`        | `https://api-teachmehipaa-dev.web.app/v1` | Building and testing; no real Learners emailed |

The default is `"live"`, so pass `environment="sandbox"` whenever you use
Sandbox credentials. Send Sandbox credentials to Live, or Live ones to the
Sandbox, and the token request fails with `OAuthError`. To aim the client
somewhere else entirely, such as a mock server, pass `base_url`: it
overrides the Environment's URL.

## Skip the Organization lookup

An API client acts for exactly one Organization, so no method takes an
`org_id`. Before the first Organization-scoped call, the client asks
`auth.introspect()` which Organization the token belongs to and remembers
the answer. Already know the id? Pass `organization_id` and the client
skips that request:

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

You can't rebind a client after you build it. Working for a second
Organization means a second client, with that Organization's credentials.

## Bring your own Access tokens

If another system issues Access tokens for you, pass a `token_provider`
in place of the id and secret. `StaticTokenProvider` sends the token you
give it, unchanged:

<!-- sample: static-token -->
```python
from teachmehipaa import StaticTokenProvider, TeachMeHipaa

client = TeachMeHipaa(
    token_provider=StaticTokenProvider(access_token),
    environment="sandbox",
)
print(client.compliance.retrieve().compliant_rate)
```

The client can't renew a static token. Once it expires, calls raise
`AuthenticationError`. `AsyncTeachMeHipaa` takes `AsyncStaticTokenProvider`.

For anything smarter, write a class with the two methods of the
`TokenProvider` protocol (`AsyncTokenProvider` for the async client):
`access_token()` returns the token to send, and
`invalidate(access_token)` discards one the API refused, so the next
`access_token()` call returns a fresh one. A client takes either
`client_id` plus `client_secret` or a `token_provider`. With a provider,
`scopes` is the provider's business.

## Look things up without credentials

`courses.list`, `courses.retrieve` and `certificate_verifications.retrieve`
are public: they send no Access token. To check a Certificate someone showed
you, build a client with no credentials at all:

<!-- sample: public-lookups -->
```python
from teachmehipaa import TeachMeHipaa

client = TeachMeHipaa(environment="sandbox")

verification = client.certificate_verifications.retrieve("aB3dE9")
print(verification.status, verification.learner_name)

for course in client.courses.list():
    print(course.title)
```

Every other method on that client raises `ValueError` before it sends a
request. `AsyncTeachMeHipaa(environment="sandbox")` behaves the same.
The API allows 60 Certificate verifications a minute from one IP address.
