"""Read-only smoke test against the real Sandbox, run by hand with
`uv run pytest -m sandbox`. Without credentials every test is skipped, and CI
never runs it."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from teachmehipaa import TeachMeHipaa

CLIENT_ID = os.environ.get("TMH_SANDBOX_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("TMH_SANDBOX_CLIENT_SECRET", "")

pytestmark = [
    pytest.mark.sandbox,
    pytest.mark.skipif(
        not (CLIENT_ID and CLIENT_SECRET),
        reason="set TMH_SANDBOX_CLIENT_ID and TMH_SANDBOX_CLIENT_SECRET",
    ),
]


@pytest.fixture
def client() -> Iterator[TeachMeHipaa]:
    with TeachMeHipaa(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, environment="sandbox"
    ) as sandbox:
        yield sandbox


def test_introspects_a_sandbox_access_token_for_an_organization(
    client: TeachMeHipaa,
) -> None:
    introspection = client.auth.introspect()

    # The spec: "`test` for a Sandbox client, `live` otherwise."
    assert introspection.mode == "test"
    assert isinstance(introspection.org_id, str)


def test_lists_courses(client: TeachMeHipaa) -> None:
    page = client.courses.list(limit=5)

    assert isinstance(page.items, list)


def test_lists_learners(client: TeachMeHipaa) -> None:
    page = client.learners.list(limit=5)

    assert isinstance(page.items, list)
    assert page.last_response.status == 200
