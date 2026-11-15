import base64
import hashlib
import re
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest

from teachmehipaa import APIConnectionError, APIError, OAuthError, oauth
from tests.fake_api import (
    APP_BASIC_CREDENTIALS,
    APP_ID,
    APP_SECRET,
    REFRESH_TOKEN_1,
    SANDBOX_BASE,
    FakeApi,
    Reply,
    grant_token_reply,
    network_error,
    oauth_error_reply,
)

UNRESERVED_43_TO_128 = re.compile(r"[A-Za-z0-9._~-]{43,128}")
BASE64URL_43 = re.compile(r"[A-Za-z0-9_-]{43}")


def s256(code_verifier: str) -> str:
    """RFC 7636 §4.2, computed here rather than by the SDK."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def test_the_code_challenge_is_the_s256_hash_of_the_code_verifier() -> None:
    pair = oauth.create_pkce_pair()

    assert pair.method == "S256"
    assert UNRESERVED_43_TO_128.fullmatch(pair.code_verifier)
    assert BASE64URL_43.fullmatch(pair.code_challenge)
    assert pair.code_challenge == s256(pair.code_verifier)


def test_every_pkce_pair_has_a_fresh_code_verifier() -> None:
    assert oauth.create_pkce_pair().code_verifier != (
        oauth.create_pkce_pair().code_verifier
    )


REDIRECT_URI = "https://partner.example.com/oauth/callback?tenant=7"
CHALLENGE = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
CONSENT: dict[str, Any] = {
    "client_id": APP_ID,
    "redirect_uri": REDIRECT_URI,
    "scopes": ["learners:read", "learners:write"],
    "state": "af0ifjsldkj",
    "code_challenge": CHALLENGE,
}


def test_the_consent_url_carries_client_redirect_scopes_state_and_s256() -> None:
    url = urlsplit(oauth.authorize_url(**CONSENT))

    assert f"{url.scheme}://{url.netloc}{url.path}" == (
        "https://console.teachmehipaa.com/oauth/authorize"
    )
    assert parse_qs(url.query) == {
        "response_type": ["code"],
        "client_id": [APP_ID],
        "redirect_uri": [REDIRECT_URI],
        "scope": ["learners:read learners:write"],
        "state": ["af0ifjsldkj"],
        "code_challenge": [CHALLENGE],
        "code_challenge_method": ["S256"],
    }


def test_the_consent_url_encodes_spaces_in_the_scope_as_percent_20() -> None:
    assert "scope=learners%3Aread%20learners%3Awrite" in oauth.authorize_url(**CONSENT)


def test_a_consent_url_needs_a_state() -> None:
    with pytest.raises(ValueError, match="state"):
        oauth.authorize_url(**{**CONSENT, "state": ""})


def test_states_are_hard_to_guess() -> None:
    state = oauth.create_state()

    assert BASE64URL_43.fullmatch(state)
    assert state != oauth.create_state()


def test_sandbox_consent_needs_an_explicit_authorization_url() -> None:
    with pytest.raises(ValueError, match="authorization_url"):
        oauth.authorize_url(**CONSENT, environment="sandbox")

    url = urlsplit(
        oauth.authorize_url(
            **CONSENT,
            environment="sandbox",
            authorization_url="https://console.example.test/oauth/authorize",
        )
    )

    assert f"{url.scheme}://{url.netloc}{url.path}" == (
        "https://console.example.test/oauth/authorize"
    )
    assert parse_qs(url.query)["code_challenge_method"] == ["S256"]


VERIFIER = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
CODE = "SplxlOBeZQQYbYS6WxSbIA"
EXCHANGE: dict[str, Any] = {
    "client_id": APP_ID,
    "client_secret": APP_SECRET,
    "code": CODE,
    "redirect_uri": REDIRECT_URI,
    "code_verifier": VERIFIER,
}


def test_the_code_exchange_returns_the_grant_tokens() -> None:
    api = FakeApi()
    api.on(
        "POST",
        "/auth/token",
        grant_token_reply("access-token-org", REFRESH_TOKEN_1, 900),
    )

    grant = oauth.exchange_code(**EXCHANGE, http_client=api.sync_client())

    assert grant == oauth.GrantTokens(
        access_token="access-token-org",
        refresh_token=REFRESH_TOKEN_1,
        expires_in=900,
        scopes=("learners:read", "learners:write"),
    )
    [exchange] = api.requests
    assert str(exchange.url) == "https://api.tme.so/v1/auth/token"
    assert exchange.headers["authorization"] == f"Basic {APP_BASIC_CREDENTIALS}"
    assert exchange.headers["content-type"] == "application/x-www-form-urlencoded"
    assert parse_qs(exchange.content.decode()) == {
        "grant_type": ["authorization_code"],
        "code": [CODE],
        "redirect_uri": [REDIRECT_URI],
        "code_verifier": [VERIFIER],
    }


def test_grant_tokens_keep_their_secrets_out_of_repr() -> None:
    grant = oauth.GrantTokens(
        access_token="access-token-org",
        refresh_token=REFRESH_TOKEN_1,
        expires_in=900,
        scopes=(),
    )

    assert "access-token-org" not in repr(grant)
    assert REFRESH_TOKEN_1 not in repr(grant)


async def test_the_async_code_exchange_returns_the_grant_tokens() -> None:
    api = FakeApi()
    api.on(
        "POST", "/auth/token", grant_token_reply("access-token-org", REFRESH_TOKEN_1)
    )

    grant = await oauth.async_exchange_code(**EXCHANGE, http_client=api.async_client())

    assert grant.refresh_token == REFRESH_TOKEN_1
    assert grant.scopes == ("learners:read", "learners:write")
    assert parse_qs(api.requests[0].content.decode())["grant_type"] == [
        "authorization_code"
    ]


def test_the_code_exchange_goes_to_the_sandbox_token_endpoint_when_asked() -> None:
    api = FakeApi(SANDBOX_BASE)
    api.on(
        "POST", "/auth/token", grant_token_reply("access-token-org", REFRESH_TOKEN_1)
    )

    oauth.exchange_code(
        **EXCHANGE, environment="sandbox", http_client=api.sync_client()
    )

    assert str(api.requests[0].url) == (
        "https://api-teachmehipaa-dev.web.app/v1/auth/token"
    )


def test_a_refused_code_raises_an_oauth_error() -> None:
    api = FakeApi()
    api.on(
        "POST",
        "/auth/token",
        oauth_error_reply("invalid_grant", "The code has expired or was used"),
    )

    with pytest.raises(OAuthError) as raised:
        oauth.exchange_code(**EXCHANGE, http_client=api.sync_client())

    assert raised.value.code == "invalid_grant"
    assert raised.value.status == 400


def test_a_network_failure_is_never_retried_and_says_the_code_may_be_spent() -> None:
    api = FakeApi()
    api.on("POST", "/auth/token", network_error)

    with pytest.raises(APIConnectionError) as raised:
        oauth.exchange_code(**EXCHANGE, http_client=api.sync_client())

    assert "consumed" in str(raised.value)
    assert "consent" in str(raised.value)
    assert len(api.requests) == 1


async def test_an_async_network_failure_is_never_retried() -> None:
    api = FakeApi()
    api.on("POST", "/auth/token", network_error)

    with pytest.raises(APIConnectionError, match="consumed"):
        await oauth.async_exchange_code(**EXCHANGE, http_client=api.async_client())

    assert len(api.requests) == 1


def test_a_server_error_is_never_retried_either() -> None:
    api = FakeApi()
    api.on(
        "POST",
        "/auth/token",
        oauth_error_reply("temporarily_unavailable", "Try later", status=503),
    )

    with pytest.raises(OAuthError):
        oauth.exchange_code(**EXCHANGE, http_client=api.sync_client())

    assert len(api.requests) == 1


def test_a_token_response_without_a_refresh_token_raises_an_api_error() -> None:
    api = FakeApi()
    api.on(
        "POST",
        "/auth/token",
        Reply(
            json={
                "access_token": "access-token-org",
                "token_type": "Bearer",
                "expires_in": 900,
            }
        ),
    )

    with pytest.raises(APIError) as raised:
        oauth.exchange_code(**EXCHANGE, http_client=api.sync_client())

    # The body holds a live Access token, which must not reach error reporters.
    assert raised.value.body is None
