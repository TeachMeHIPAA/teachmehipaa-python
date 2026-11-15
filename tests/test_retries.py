import httpx
import pytest

from teachmehipaa import (
    APIConnectionError,
    APIError,
    AsyncTeachMeHipaa,
    ConflictError,
    OAuthError,
    RateLimitError,
    TeachMeHipaa,
    TeachMeHipaaError,
)
from tests.fake_api import (
    CLIENT_ID,
    CLIENT_SECRET,
    LEARNER_ID,
    LEARNER_JSON,
    ORG_ID,
    FakeApi,
    FakeAsyncSleep,
    FakeSleep,
    Reply,
    Responder,
    network_error,
    problem,
    read_timeout,
    token_json,
)

LEARNER_PATH = f"/organizations/{ORG_ID}/learners/{LEARNER_ID}"
OK = Reply(json=LEARNER_JSON)


def make_client(
    api: FakeApi, sleep: FakeSleep, *, max_retries: int = 2
) -> TeachMeHipaa:
    return TeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        max_retries=max_retries,
        http_client=api.sync_client(),
        sleep=sleep,
    )


def script(api: FakeApi, method: str, path: str, *replies: Reply | Responder) -> None:
    api.replace(method, path, replies[0])
    for reply in replies[1:]:
        api.on(method, path, reply)


def attempts(api: FakeApi) -> int:
    return len(api.requests_to("GET", LEARNER_PATH))


@pytest.mark.parametrize(
    "transient",
    [
        problem(500, "internal"),
        problem(502, "refund_failed"),
        problem(503, "temporarily_unavailable"),
        problem(429, "rate_limited"),
        problem(409, "conflict"),
        network_error,
        read_timeout,
    ],
    ids=["500", "502", "503", "429", "409-conflict", "network", "timeout"],
)
def test_a_get_is_retried_after_a_transient_failure(
    api: FakeApi, transient: Reply | Responder
) -> None:
    script(api, "GET", LEARNER_PATH, transient, OK)
    sleep = FakeSleep()

    learner = make_client(api, sleep).learners.retrieve(LEARNER_ID)

    assert learner.learner_id == LEARNER_ID
    assert attempts(api) == 2
    assert len(sleep.waits) == 1


@pytest.mark.parametrize(
    "permanent",
    [
        problem(400, "validation_failed"),
        problem(404, "not_found"),
        problem(409, "seat_unavailable"),
        problem(412, "precondition_failed"),
        problem(422, "validation_failed"),
    ],
    ids=["400", "404", "409-seat_unavailable", "412", "422"],
)
def test_a_permanent_failure_is_not_retried(api: FakeApi, permanent: Reply) -> None:
    script(api, "GET", LEARNER_PATH, permanent, OK)
    sleep = FakeSleep()

    with pytest.raises(TeachMeHipaaError):
        make_client(api, sleep).learners.retrieve(LEARNER_ID)

    assert attempts(api) == 1
    assert sleep.waits == []


def test_retries_twice_by_default_then_raises_the_last_error(api: FakeApi) -> None:
    script(api, "GET", LEARNER_PATH, problem(503, "temporarily_unavailable"))
    sleep = FakeSleep()

    with pytest.raises(APIError) as raised:
        make_client(api, sleep).learners.retrieve(LEARNER_ID)

    assert raised.value.status == 503
    assert attempts(api) == 3
    assert len(sleep.waits) == 2


def test_backoff_starts_at_half_a_second_and_doubles_to_a_5_second_cap(
    api: FakeApi,
) -> None:
    script(api, "GET", LEARNER_PATH, problem(503, "temporarily_unavailable"))
    sleep = FakeSleep()

    with pytest.raises(APIError):
        make_client(api, sleep, max_retries=6).learners.retrieve(LEARNER_ID)

    # Jitter shortens each nominal delay by at most half, never below 0.5 s.
    nominal = [0.5, 1.0, 2.0, 4.0, 5.0, 5.0]
    assert len(sleep.waits) == len(nominal)
    for waited, delay in zip(sleep.waits, nominal, strict=True):
        assert max(0.5, delay / 2) <= waited <= delay


def test_jitter_spreads_the_waits_of_repeated_calls(api: FakeApi) -> None:
    script(api, "GET", LEARNER_PATH, problem(503, "temporarily_unavailable"))
    sleep = FakeSleep()
    client = make_client(api, sleep, max_retries=3)

    for _ in range(10):
        with pytest.raises(APIError):
            client.learners.retrieve(LEARNER_ID)

    third_waits = sleep.waits[2::3]
    assert len(set(third_waits)) > 1


def test_retry_after_is_honored(api: FakeApi) -> None:
    rate_limited = problem(429, "rate_limited", headers={"retry-after": "7"})
    script(api, "GET", LEARNER_PATH, rate_limited, OK)
    sleep = FakeSleep()

    make_client(api, sleep).learners.retrieve(LEARNER_ID)

    assert sleep.waits == [7.0]


def test_retry_after_is_capped_at_60_seconds(api: FakeApi) -> None:
    rate_limited = problem(429, "rate_limited", headers={"retry-after": "3600"})
    script(api, "GET", LEARNER_PATH, rate_limited, OK)
    sleep = FakeSleep()

    make_client(api, sleep).learners.retrieve(LEARNER_ID)

    assert sleep.waits == [60.0]


def test_a_retry_after_on_a_503_is_honored_too(api: FakeApi) -> None:
    unavailable = problem(503, "temporarily_unavailable", headers={"retry-after": "2"})
    script(api, "GET", LEARNER_PATH, unavailable, OK)
    sleep = FakeSleep()

    make_client(api, sleep).learners.retrieve(LEARNER_ID)

    assert sleep.waits == [2.0]


def test_exhausted_retries_raise_the_rate_limit_error(api: FakeApi) -> None:
    script(api, "GET", LEARNER_PATH, problem(429, "rate_limited"))

    with pytest.raises(RateLimitError):
        make_client(api, FakeSleep()).learners.retrieve(LEARNER_ID)


def test_exhausted_retries_after_network_errors_raise_a_connection_error(
    api: FakeApi,
) -> None:
    script(api, "GET", LEARNER_PATH, network_error)

    with pytest.raises(APIConnectionError) as raised:
        make_client(api, FakeSleep()).learners.retrieve(LEARNER_ID)

    assert isinstance(raised.value.__cause__, httpx.ConnectError)
    assert attempts(api) == 3


def test_max_retries_zero_on_the_client_disables_retries(api: FakeApi) -> None:
    script(api, "GET", LEARNER_PATH, problem(503, "temporarily_unavailable"), OK)
    sleep = FakeSleep()

    with pytest.raises(APIError):
        make_client(api, sleep, max_retries=0).learners.retrieve(LEARNER_ID)

    assert attempts(api) == 1


def test_max_retries_per_request_overrides_the_client(api: FakeApi) -> None:
    script(api, "GET", LEARNER_PATH, problem(503, "temporarily_unavailable"))
    client = make_client(api, FakeSleep(), max_retries=0)

    with pytest.raises(APIError):
        client.learners.retrieve(LEARNER_ID, max_retries=4)

    assert attempts(api) == 5


def test_a_negative_per_request_max_retries_is_rejected(api: FakeApi) -> None:
    with pytest.raises(ValueError, match="max_retries"):
        make_client(api, FakeSleep()).learners.retrieve(LEARNER_ID, max_retries=-1)


def test_the_default_timeout_is_80_seconds(api: FakeApi) -> None:
    client = make_client(api, FakeSleep())

    client.learners.retrieve(LEARNER_ID)

    assert client.timeout == httpx.Timeout(80.0)
    [request] = api.requests_to("GET", LEARNER_PATH)
    assert request.extensions["timeout"] == httpx.Timeout(80.0).as_dict()


def test_timeout_per_request_overrides_the_client(api: FakeApi) -> None:
    make_client(api, FakeSleep()).learners.retrieve(LEARNER_ID, timeout=5.0)

    [request] = api.requests_to("GET", LEARNER_PATH)
    assert request.extensions["timeout"] == httpx.Timeout(5.0).as_dict()


def test_a_client_credentials_mint_is_retried() -> None:
    api = FakeApi()
    api.on(
        "POST",
        "/auth/token",
        Reply(
            status=429,
            json={"error": "slow_down", "error_description": "Slow down."},
            headers={"retry-after": "3"},
        ),
    )
    api.on("POST", "/auth/token", Reply(json=token_json()))
    api.on("GET", LEARNER_PATH, OK)
    sleep = FakeSleep()

    make_client(api, sleep).learners.retrieve(LEARNER_ID)

    assert len(api.requests_to("POST", "/auth/token")) == 2
    assert sleep.waits == [3.0]


def test_a_rejected_client_credential_is_not_retried() -> None:
    api = FakeApi()
    api.on(
        "POST",
        "/auth/token",
        Reply(status=401, json={"error": "invalid_client"}),
    )
    sleep = FakeSleep()

    with pytest.raises(OAuthError):
        make_client(api, sleep).learners.retrieve(LEARNER_ID)

    assert len(api.requests_to("POST", "/auth/token")) == 1
    assert sleep.waits == []


async def test_the_async_client_retries_with_its_injected_sleep(api: FakeApi) -> None:
    script(api, "GET", LEARNER_PATH, problem(409, "conflict"), network_error, OK)
    sleep = FakeAsyncSleep()
    client = AsyncTeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.async_client(),
        sleep=sleep,
    )

    learner = await client.learners.retrieve(LEARNER_ID)

    assert learner.learner_id == LEARNER_ID
    assert attempts(api) == 3
    assert len(sleep.waits) == 2


async def test_the_async_client_honors_per_request_settings(api: FakeApi) -> None:
    script(api, "GET", LEARNER_PATH, problem(503, "temporarily_unavailable"))
    client = AsyncTeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.async_client(),
        sleep=FakeAsyncSleep(),
    )

    with pytest.raises(APIError):
        await client.learners.retrieve(LEARNER_ID, max_retries=0, timeout=3.0)

    [request] = api.requests_to("GET", LEARNER_PATH)
    assert request.extensions["timeout"] == httpx.Timeout(3.0).as_dict()


def test_a_conflict_error_still_exposes_its_code_after_retries(api: FakeApi) -> None:
    script(api, "GET", LEARNER_PATH, problem(409, "conflict"))

    with pytest.raises(ConflictError) as raised:
        make_client(api, FakeSleep()).learners.retrieve(LEARNER_ID)

    assert raised.value.code == "conflict"
    assert attempts(api) == 3
