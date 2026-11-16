import pytest

import teachmehipaa
from teachmehipaa import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncTeachMeHipaa,
    AuthenticationError,
    ConflictError,
    FieldError,
    IdempotencyError,
    InvalidRequestError,
    NotFoundError,
    OAuthError,
    PermissionDeniedError,
    PreconditionFailedError,
    RateLimitError,
    TeachMeHipaa,
    TeachMeHipaaError,
)
from tests.fake_api import (
    CLIENT_ID,
    CLIENT_SECRET,
    LEARNER_ID,
    ORG_ID,
    REQUEST_ID,
    FakeApi,
    Reply,
    network_error,
    problem,
    read_timeout,
)

LEARNER_PATH = f"/organizations/{ORG_ID}/learners/{LEARNER_ID}"


def make_client(api: FakeApi) -> TeachMeHipaa:
    return TeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        max_retries=0,
        http_client=api.sync_client(),
    )


def retrieve_failing_with(api: FakeApi, reply: Reply) -> TeachMeHipaaError:
    api.replace("GET", LEARNER_PATH, reply)
    with pytest.raises(TeachMeHipaaError) as raised:
        make_client(api).learners.retrieve(LEARNER_ID)
    return raised.value


@pytest.mark.parametrize(
    ("status", "code", "error_class"),
    [
        (400, "validation_failed", InvalidRequestError),
        (401, "unauthorized", AuthenticationError),
        (403, "org_not_active", PermissionDeniedError),
        (404, "not_found", NotFoundError),
        (405, "method_not_allowed", InvalidRequestError),
        (406, "not_acceptable", InvalidRequestError),
        (409, "seat_unavailable", ConflictError),
        (412, "precondition_failed", PreconditionFailedError),
        (415, "unsupported_media_type", InvalidRequestError),
        (422, "validation_failed", InvalidRequestError),
        (428, "precondition_required", PreconditionFailedError),
        (429, "rate_limited", RateLimitError),
        (500, "internal", APIError),
        (502, "refund_failed", APIError),
        (503, "temporarily_unavailable", APIError),
    ],
)
def test_each_status_raises_its_error_class(
    api: FakeApi, status: int, code: str, error_class: type[TeachMeHipaaError]
) -> None:
    error = retrieve_failing_with(api, problem(status, code))

    assert type(error) is error_class
    assert (error.status, error.code) == (status, code)


def test_idempotency_key_reuse_raises_the_idempotency_error(api: FakeApi) -> None:
    error = retrieve_failing_with(api, problem(422, "idempotency_key_reuse"))

    assert isinstance(error, IdempotencyError)
    assert isinstance(error, InvalidRequestError)


def test_an_unknown_code_is_kept_as_an_open_string(api: FakeApi) -> None:
    error = retrieve_failing_with(api, problem(409, "brand_new_conflict"))

    assert isinstance(error, ConflictError)
    assert error.code == "brand_new_conflict"


def test_the_error_carries_every_problem_field(api: FakeApi) -> None:
    error = retrieve_failing_with(
        api,
        problem(
            422,
            "validation_failed",
            title="Validation failed",
            detail="2 fields are invalid.",
            errors=[
                {"path": "email", "message": "Invalid email"},
                {"path": "Idempotency-Key", "message": "Required"},
            ],
        ),
    )

    assert error.title == "Validation failed"
    assert error.detail == "2 fields are invalid."
    assert error.errors == (
        FieldError(path="email", message="Invalid email"),
        FieldError(path="Idempotency-Key", message="Required"),
    )
    assert error.request_id == REQUEST_ID
    assert error.headers["content-type"] == "application/problem+json"
    assert error.body is not None
    assert '"Invalid email"' in error.body
    assert str(error) == f"2 fields are invalid. (request id: {REQUEST_ID})"


def test_a_rate_limit_error_carries_retry_after(api: FakeApi) -> None:
    error = retrieve_failing_with(
        api, problem(429, "rate_limited", headers={"retry-after": "7"})
    )

    assert isinstance(error, RateLimitError)
    assert error.retry_after == 7.0


def test_a_200_html_page_raises_an_api_error_not_a_parse_error(api: FakeApi) -> None:
    error = retrieve_failing_with(
        api,
        Reply(
            status=200,
            content_type="text/html; charset=utf-8",
            text="<!doctype html><html><body>Nuxt</body></html>",
        ),
    )

    assert type(error) is APIError
    assert error.status == 200
    assert error.code is None
    assert error.body == "<!doctype html><html><body>Nuxt</body></html>"
    assert "text/html" in str(error)


def test_an_html_error_page_raises_an_api_error(api: FakeApi) -> None:
    error = retrieve_failing_with(
        api, Reply(status=404, content_type="text/html", text="<html>404</html>")
    )

    assert type(error) is APIError
    assert error.status == 404


def test_the_gateway_envelope_without_a_problem_still_raises_an_api_error(
    api: FakeApi,
) -> None:
    error = retrieve_failing_with(
        api,
        Reply(
            status=503,
            json={"statusCode": 503, "statusMessage": "Service Unavailable"},
        ),
    )

    assert type(error) is APIError
    assert (error.status, error.code) == (503, None)


def test_a_token_endpoint_error_raises_the_oauth_error() -> None:
    api = FakeApi()
    api.on(
        "POST",
        "/auth/token",
        Reply(
            status=400,
            json={"error": "invalid_scope", "error_description": "Unknown scope."},
            headers={"x-request-id": "req_token"},
        ),
    )

    with pytest.raises(OAuthError) as raised:
        make_client(api).learners.retrieve(LEARNER_ID)

    error = raised.value
    assert (error.status, error.code) == (400, "invalid_scope")
    assert error.detail == "Unknown scope."
    assert error.request_id == "req_token"


def test_no_response_raises_a_connection_error(api: FakeApi) -> None:
    api.replace("GET", LEARNER_PATH, network_error)

    with pytest.raises(APIConnectionError) as raised:
        make_client(api).learners.retrieve(LEARNER_ID)

    assert raised.value.status is None
    assert not isinstance(raised.value, APITimeoutError)


def test_a_timeout_raises_the_timeout_error(api: FakeApi) -> None:
    api.replace("GET", LEARNER_PATH, read_timeout)

    with pytest.raises(APITimeoutError) as raised:
        make_client(api).learners.retrieve(LEARNER_ID)

    assert isinstance(raised.value, APIConnectionError)


async def test_the_async_client_maps_errors_the_same_way(api: FakeApi) -> None:
    api.replace("GET", LEARNER_PATH, problem(404, "not_found"))
    client = AsyncTeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        max_retries=0,
        http_client=api.async_client(),
    )

    with pytest.raises(NotFoundError):
        await client.learners.retrieve(LEARNER_ID)


def test_error_classes_do_not_shadow_python_builtins() -> None:
    assert not hasattr(teachmehipaa, "PermissionError")
    assert not hasattr(teachmehipaa, "ConnectionError")
    assert not hasattr(teachmehipaa, "TimeoutError")
