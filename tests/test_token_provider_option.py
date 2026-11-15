from typing import Any

import pytest

from teachmehipaa import (
    AsyncStaticTokenProvider,
    AsyncTeachMeHipaa,
    AuthenticationError,
    StaticTokenProvider,
    TeachMeHipaa,
)
from tests.fake_api import (
    APP_BASIC_CREDENTIALS,
    APP_ID,
    APP_SECRET,
    CLIENT_ID,
    CLIENT_SECRET,
    LEARNER_ID,
    LEARNER_JSON,
    ORG_ID,
    FakeApi,
    Reply,
    problem,
)

LEARNER_PATH = f"/organizations/{ORG_ID}/learners/{LEARNER_ID}"
UNAUTHORIZED = problem(401, "unauthorized", title="Unauthorized")


def bearers(api: FakeApi) -> list[str]:
    return [r.headers["authorization"] for r in api.requests_to("GET", LEARNER_PATH)]


def test_a_static_token_is_sent_as_is_and_the_token_endpoint_is_never_called() -> None:
    api = FakeApi()
    api.on("GET", LEARNER_PATH, Reply(json=LEARNER_JSON))
    client = TeachMeHipaa(
        token_provider=StaticTokenProvider("access-token-from-elsewhere"),
        organization_id=ORG_ID,
        http_client=api.sync_client(),
    )

    client.learners.retrieve(LEARNER_ID)
    client.learners.retrieve(LEARNER_ID)

    assert api.requests_to("POST", "/auth/token") == []
    assert bearers(api) == ["Bearer access-token-from-elsewhere"] * 2


def test_a_static_token_refused_with_401_is_sent_once() -> None:
    api = FakeApi()
    api.on("GET", LEARNER_PATH, UNAUTHORIZED)
    client = TeachMeHipaa(
        token_provider=StaticTokenProvider("access-token-expired"),
        organization_id=ORG_ID,
        http_client=api.sync_client(),
    )

    with pytest.raises(AuthenticationError):
        client.learners.retrieve(LEARNER_ID)

    assert len(api.requests) == 1


async def test_an_async_static_token_refused_with_401_is_sent_once() -> None:
    api = FakeApi()
    api.on("GET", LEARNER_PATH, UNAUTHORIZED)
    client = AsyncTeachMeHipaa(
        token_provider=AsyncStaticTokenProvider("access-token-expired"),
        organization_id=ORG_ID,
        http_client=api.async_client(),
    )

    with pytest.raises(AuthenticationError):
        await client.learners.retrieve(LEARNER_ID)

    assert len(api.requests) == 1
    assert api.requests_to("POST", "/auth/token") == []


def test_a_static_token_must_not_be_empty() -> None:
    with pytest.raises(ValueError, match="access_token must be a non-empty string"):
        StaticTokenProvider("")


@pytest.mark.parametrize(
    "conflicting",
    [
        {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
        {"client_id": CLIENT_ID},
        {"scopes": ["learners:read"]},
    ],
)
def test_a_token_provider_cannot_be_combined_with_credentials_or_scopes(
    conflicting: dict[str, Any],
) -> None:
    with pytest.raises(TypeError, match="either token_provider or client_id"):
        TeachMeHipaa(token_provider=StaticTokenProvider("jwt"), **conflicting)


def test_the_async_client_refuses_a_token_provider_with_credentials() -> None:
    with pytest.raises(TypeError, match="either token_provider or client_id"):
        AsyncTeachMeHipaa(
            token_provider=AsyncStaticTokenProvider("jwt"),
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
        )


def test_a_client_needs_credentials_or_a_token_provider() -> None:
    with pytest.raises(TypeError, match="client_id and client_secret"):
        TeachMeHipaa(client_id=CLIENT_ID)


def test_a_partner_apps_own_credentials_call_partners_without_an_organization() -> None:
    partner_id = "ptn_01JD82ZX4C5V6B7N8M9Q0W1E2R"
    api = FakeApi()
    api.on(
        "POST",
        "/auth/token",
        Reply(
            json={
                "access_token": "access-token-partner",
                "token_type": "Bearer",
                "expires_in": 900,
                "scope": "partner:orgs:read partner:orgs:write",
            }
        ),
    )
    api.on(
        "GET",
        f"/partners/{partner_id}",
        Reply(
            json={
                "partnerId": partner_id,
                "name": "Reseller Co",
                "appId": APP_ID,
                "status": "active",
                "maxChildOrgs": 50,
                "childOrgCount": 3,
                "createdAt": "2026-11-01T09:00:00.000Z",
            }
        ),
    )
    client = TeachMeHipaa(
        client_id=APP_ID, client_secret=APP_SECRET, http_client=api.sync_client()
    )

    partner = client.partners.retrieve(partner_id)

    assert partner.partner_id == partner_id
    assert api.requests_to("GET", "/auth/introspection") == []
    [mint] = api.requests_to("POST", "/auth/token")
    assert mint.headers["authorization"] == f"Basic {APP_BASIC_CREDENTIALS}"
    [call] = api.requests_to("GET", f"/partners/{partner_id}")
    assert call.headers["authorization"] == "Bearer access-token-partner"
