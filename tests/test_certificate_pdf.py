"""Certificate PDF downloads, whole and streamed, through the public client."""

import pytest

from teachmehipaa import (
    APIError,
    AsyncBinaryStream,
    AsyncTeachMeHipaa,
    BinaryResponse,
    BinaryStream,
    NotFoundError,
    TeachMeHipaa,
)
from tests.fake_api import (
    CLIENT_ID,
    CLIENT_SECRET,
    ORG_ID,
    FakeApi,
    FakeAsyncSleep,
    FakeSleep,
    Reply,
    problem,
    token_json,
)

CERTIFICATE_ID = "cert_01JD8F"
PATH = f"/organizations/{ORG_ID}/certificates/{CERTIFICATE_ID}/content"
ACCEPT = "application/pdf, application/problem+json"

# Every byte value, so any text decoding along the way would show.
EVERY_BYTE = bytes(range(256))

PDF = Reply(
    content=EVERY_BYTE,
    content_type="application/pdf",
    headers={"content-disposition": 'attachment; filename="certificate-ana.pdf"'},
)
NOT_FOUND = problem(404, "not_found", title="Not found", detail="No such certificate.")
HTML_PAGE = Reply(
    text="<!doctype html><title>Not found</title>", content_type="text/html"
)


@pytest.fixture
def api() -> FakeApi:
    fake = FakeApi()
    fake.on("POST", "/auth/token", Reply(json=token_json()))
    return fake


def make_client(api: FakeApi) -> TeachMeHipaa:
    return TeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.sync_client(),
        sleep=FakeSleep(),
    )


def make_async_client(api: FakeApi) -> AsyncTeachMeHipaa:
    return AsyncTeachMeHipaa(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        organization_id=ORG_ID,
        http_client=api.async_client(),
        sleep=FakeAsyncSleep(),
    )


# --- Whole file -----------------------------------------------------------


def test_every_byte_comes_back_unchanged_with_type_and_filename(api: FakeApi) -> None:
    api.on("GET", PATH, PDF)

    pdf: BinaryResponse = make_client(api).certificates.download_pdf(CERTIFICATE_ID)

    assert pdf.content == EVERY_BYTE
    assert pdf.content_type == "application/pdf"
    assert pdf.filename == "certificate-ana.pdf"
    assert pdf.last_response.status == 200
    [request] = api.requests_to("GET", PATH)
    assert request.headers["accept"] == ACCEPT


async def test_async_every_byte_comes_back_unchanged(api: FakeApi) -> None:
    api.on("GET", PATH, PDF)

    pdf = await make_async_client(api).certificates.download_pdf(CERTIFICATE_ID)

    assert pdf.content == EVERY_BYTE
    assert pdf.filename == "certificate-ana.pdf"


def test_a_utf8_filename_is_preferred_over_the_plain_one(api: FakeApi) -> None:
    disposition = (
        'attachment; filename="certificate-jose.pdf"; '
        "filename*=UTF-8''certificate-jos%C3%A9.pdf"
    )
    api.on(
        "GET",
        PATH,
        Reply(
            content=EVERY_BYTE,
            content_type="application/pdf",
            headers={"content-disposition": disposition},
        ),
    )

    pdf = make_client(api).certificates.download_pdf(CERTIFICATE_ID)

    assert pdf.filename == "certificate-josé.pdf"


def test_a_problem_response_raises_the_typed_error(api: FakeApi) -> None:
    api.on("GET", PATH, NOT_FOUND)

    with pytest.raises(NotFoundError) as raised:
        make_client(api).certificates.download_pdf(CERTIFICATE_ID)

    assert raised.value.code == "not_found"
    assert raised.value.request_id == "req_7f3c2a"


def test_an_html_page_is_not_handed_back_as_a_pdf(api: FakeApi) -> None:
    api.on("GET", PATH, HTML_PAGE)

    with pytest.raises(APIError):
        make_client(api).certificates.download_pdf(CERTIFICATE_ID)


# --- Streamed -------------------------------------------------------------


def test_a_stream_yields_every_byte_unchanged(api: FakeApi) -> None:
    api.on("GET", PATH, PDF)

    with make_client(api).certificates.download_pdf(CERTIFICATE_ID, stream=True) as pdf:
        assert isinstance(pdf, BinaryStream)
        assert pdf.content_type == "application/pdf"
        assert pdf.filename == "certificate-ana.pdf"
        assert pdf.last_response.status == 200
        received = b"".join(pdf.iter_bytes(chunk_size=100))

    assert received == EVERY_BYTE
    [request] = api.requests_to("GET", PATH)
    assert request.headers["accept"] == ACCEPT


async def test_async_a_stream_yields_every_byte_unchanged(api: FakeApi) -> None:
    api.on("GET", PATH, PDF)

    async with await make_async_client(api).certificates.download_pdf(
        CERTIFICATE_ID, stream=True
    ) as pdf:
        assert isinstance(pdf, AsyncBinaryStream)
        assert pdf.filename == "certificate-ana.pdf"
        received = b"".join([chunk async for chunk in pdf.aiter_bytes()])

    assert received == EVERY_BYTE


def test_a_streamed_download_is_retried_until_the_file_starts(api: FakeApi) -> None:
    api.on("GET", PATH, problem(503, "temporarily_unavailable"))
    api.on("GET", PATH, PDF)

    with make_client(api).certificates.download_pdf(CERTIFICATE_ID, stream=True) as pdf:
        assert pdf.read() == EVERY_BYTE

    assert len(api.requests_to("GET", PATH)) == 2


def test_a_streamed_problem_response_raises_the_typed_error(api: FakeApi) -> None:
    api.on("GET", PATH, NOT_FOUND)

    with pytest.raises(NotFoundError):
        make_client(api).certificates.download_pdf(CERTIFICATE_ID, stream=True)


async def test_async_an_html_page_raises_before_any_stream(api: FakeApi) -> None:
    api.on("GET", PATH, HTML_PAGE)

    with pytest.raises(APIError):
        await make_async_client(api).certificates.download_pdf(
            CERTIFICATE_ID, stream=True
        )
