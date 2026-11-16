# Exceptions

Every failure the API reports, or a missing response, raises a subclass of
`TeachMeHipaaError`. Import any of them from `teachmehipaa`. The class
follows the HTTP status, so you can catch as narrowly or broadly as you like.

```text
TeachMeHipaaError
├── InvalidRequestError        400, 405, 406, 415, 422
│   └── IdempotencyError       422 idempotency_key_reuse
├── AuthenticationError        401
├── PermissionDeniedError      403, such as a missing Scope
├── NotFoundError              404
├── ConflictError              409
├── PreconditionFailedError    412 stale ETag, 428 missing if_match
├── RateLimitError             429, with retry_after in seconds
├── APIError                   5xx, or a body that isn't JSON
├── APIConnectionError         no response arrived
│   └── APITimeoutError        no response within timeout
├── OAuthError                 the token endpoint refused your credentials
├── OperationFailedError       an Operation finished with an error
├── OperationTimeoutError      wait() ran out of time
└── WebhookSignatureError      a Delivery failed verification
```

The last three come from helpers: `wait()` (see
[Exports, imports and PDFs](files-and-operations.md)) and webhook
verification (see [Webhooks](webhooks.md)). The acronyms stay upper case,
as PEP 8 recommends: `APIError`, `OAuthError`.

Two kinds of mistake raise built-in exceptions instead, since the API never
saw them. Bad client options raise `TypeError` or `ValueError` when you
build the client. A credential-less client raises `ValueError` if you call a
method that needs a token.

## Catch an error and find out why

<!-- sample: errors -->
```python
from teachmehipaa import NotFoundError, PermissionDeniedError, TeachMeHipaaError

try:
    client.learners.retrieve("sub_01JD80AB2C3D4E5F6G7H8J9K0M")
except NotFoundError:
    print("No such Learner")
except PermissionDeniedError as error:
    print("Missing a Scope:", error.detail)
except TeachMeHipaaError as error:
    print(error.code, error.detail, error.request_id)
    for field in error.errors:
        print(field.path, field.message)
```

(Samples in this guide use a `client` built as in the
[Quickstart](quickstart.md#make-a-request).)

The API answers errors with Problem Details, and the exception carries them
as attributes:

| Attribute                        | What it holds                                                       |
| -------------------------------- | ------------------------------------------------------------------- |
| `code`                           | A machine-readable code, such as `not_found` or `external_id_conflict` |
| `title`, `detail`                | A human-readable summary and explanation                            |
| `errors`                         | A list of `FieldError`, each with a `path` and a `message`          |
| `status`, `headers`              | From the HTTP response                                              |
| `request_id`                     | The id TeachMeHIPAA support can look the call up by                 |
| `message`                        | `detail`, else `title`, else `code`                                 |

Branch on `code`, never on the wording of `detail`. The API adds codes over
time, so give every `if`/`match` on `code` a fallback arm. `str(error)` is
`message` with the request id appended, which makes it a good log line as
it stands.

## Quote a request id to support

Every response carries a request id: `error.request_id` on a failure,
`last_response.request_id` on a success. Paste it into your support ticket
and TeachMeHIPAA can find the exact call.

You can also choose the id. Pass `request_id="..."` to any method and the
client sends it as `x-request-id` on every attempt, so one id ties your logs
to TeachMeHIPAA's. The API echoes ids that match `^[A-Za-z0-9._-]{1,128}$`
and swaps any other for one of its own.
[Retries and timeouts](retries-and-timeouts.md#override-settings-for-one-call)
shows it next to the other per-call options.
