import asyncio

import pytest

from teachmehipaa import AsyncTeachMeHipaa, TeachMeHipaa, TeachMeHipaaError
from tests.fake_api import (
    ACCESS_TOKEN,
    CLIENT_ID,
    CLIENT_SECRET,
    LEARNER_ID,
    LEARNER_JSON,
    FakeApi,
    Reply,
    introspection_json,
    token_json,
)


def test_discovers_the_organization_once_and_reuses_it(api: FakeApi) -> None:
    client = TeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, http_client=api.sync_client()
    )

    client.learners.retrieve(LEARNER_ID)
    client.learners.retrieve(LEARNER_ID)

    [introspection] = api.requests_to("GET", "/auth/introspection")
    assert introspection.headers["authorization"] == f"Bearer {ACCESS_TOKEN}"
    assert [r.url.path for r in api.requests[-2:]] == [
        f"/v1/organizations/org_acme/learners/{LEARNER_ID}"
    ] * 2


def test_an_explicit_organization_id_skips_discovery() -> None:
    api = FakeApi()
    api.on("POST", "/auth/token", Reply(json=token_json()))
    api.on(
        "GET",
        f"/organizations/org_given/learners/{LEARNER_ID}",
        Reply(json=LEARNER_JSON),
    )
    client = TeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id="org_given",
        http_client=api.sync_client(),
    )

    learner = client.learners.retrieve(LEARNER_ID)

    assert learner.learner_id == LEARNER_ID
    assert api.requests_to("GET", "/auth/introspection") == []


async def test_concurrent_async_calls_discover_the_organization_once(
    api: FakeApi,
) -> None:
    client = AsyncTeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, http_client=api.async_client()
    )

    await asyncio.gather(*(client.learners.retrieve(LEARNER_ID) for _ in range(5)))

    assert len(api.requests_to("GET", "/auth/introspection")) == 1
    assert len(api.requests_to("POST", "/auth/token")) == 1


def test_a_token_bound_to_no_organization_raises() -> None:
    api = FakeApi()
    api.on("POST", "/auth/token", Reply(json=token_json()))
    api.on("GET", "/auth/introspection", Reply(json=introspection_json(org_id=None)))
    client = TeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, http_client=api.sync_client()
    )

    with pytest.raises(
        TeachMeHipaaError,
        match=r"^The Access token is not bound to an Organization\. "
        r"Pass organization_id when you create the client\.$",
    ):
        client.learners.retrieve(LEARNER_ID)
