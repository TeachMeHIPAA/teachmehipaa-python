import httpx
import pytest

from teachmehipaa import AsyncTeachMeHipaa, TeachMeHipaa
from tests.fake_api import (
    CLIENT_ID,
    CLIENT_SECRET,
    LEARNER_ID,
    SANDBOX_BASE,
    FakeApi,
    script_learner_retrieve,
)


def hosts_called(api: FakeApi) -> set[str]:
    return {str(r.url.copy_with(path="/")) for r in api.requests}


def test_defaults_to_the_live_environment(api: FakeApi) -> None:
    client = TeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, http_client=api.sync_client()
    )

    client.learners.retrieve(LEARNER_ID)

    assert client.environment == "live"
    assert client.base_url == "https://api.tme.so/v1"
    assert hosts_called(api) == {"https://api.tme.so/"}


def test_sandbox_environment_calls_the_sandbox_deployment() -> None:
    api = FakeApi(SANDBOX_BASE)
    script_learner_retrieve(api)
    client = TeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        environment="sandbox",
        http_client=api.sync_client(),
    )

    client.learners.retrieve(LEARNER_ID)

    assert client.base_url == "https://sandbox.api.tme.so/v1"
    assert hosts_called(api) == {"https://sandbox.api.tme.so/"}
    assert api.requests[0].url.path == "/v1/auth/token"


def test_base_url_overrides_the_environment() -> None:
    api = FakeApi("http://localhost:4010")
    script_learner_retrieve(api)
    client = TeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        environment="sandbox",
        base_url="http://localhost:4010/",
        http_client=api.sync_client(),
    )

    client.learners.retrieve(LEARNER_ID)

    assert hosts_called(api) == {"http://localhost:4010/"}
    assert api.requests[0].url.path == "/auth/token"


def test_rejects_an_unknown_environment() -> None:
    with pytest.raises(ValueError, match="environment"):
        TeachMeHipaa(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            environment="staging",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("setting", ["environment", "base_url", "max_retries"])
def test_configuration_cannot_be_changed_after_construction(setting: str) -> None:
    client = TeachMeHipaa(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

    with pytest.raises(AttributeError):
        setattr(client, setting, "changed")


def test_exposes_retry_and_timeout_settings() -> None:
    client = TeachMeHipaa(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    tuned = TeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, max_retries=5, timeout=12.5
    )

    assert client.max_retries == 2
    assert (tuned.max_retries, tuned.timeout) == (5, httpx.Timeout(12.5))


def test_identifies_the_sdk_and_app_in_the_user_agent(api: FakeApi) -> None:
    client = TeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        app_info={"name": "AcmeHR", "version": "4.2", "url": "https://acme.example"},
        http_client=api.sync_client(),
    )

    client.learners.retrieve(LEARNER_ID)

    for request in api.requests:
        agent = request.headers["user-agent"]
        assert agent.startswith("teachmehipaa-python/")
        assert agent.endswith(" AcmeHR/4.2 (https://acme.example)")


def test_closing_the_client_closes_its_http_client(api: FakeApi) -> None:
    http_client = api.sync_client()

    with TeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, http_client=http_client
    ) as client:
        client.learners.retrieve(LEARNER_ID)

    assert http_client.is_closed


async def test_closing_the_async_client_closes_its_http_client(api: FakeApi) -> None:
    http_client = api.async_client()

    async with AsyncTeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, http_client=http_client
    ) as client:
        await client.learners.retrieve(LEARNER_ID)

    assert http_client.is_closed
