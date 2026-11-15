"""Enrollment CSV imports as multipart bodies, through the public client."""

import io
import json
import re
from collections.abc import Callable
from email import message_from_bytes
from email.message import Message
from pathlib import Path
from typing import Any

import httpx
import pytest

from teachmehipaa import AsyncTeachMeHipaa, FileInput, TeachMeHipaa
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

PATH = f"/organizations/{ORG_ID}/enrollments:import"
UUID_V4 = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

# RFC 4180 with CRLF, a quoted comma and non-ASCII UTF-8.
CSV_TEXT = (
    'email,name\r\nana@example.com,"Example, Ana"\r\njose@example.com,José Núñez\r\n'
)
CSV = CSV_TEXT.encode()

# `dev#/components/schemas/ImportPreview`.
PREVIEW_JSON: dict[str, Any] = {
    "totalRows": 2,
    "validRows": 2,
    "seatsRequired": 2,
    "seatsAvailable": 10,
    "rows": [
        {
            "rowNumber": 2,
            "email": "ana@example.com",
            "courseId": "hipaa-2026",
            "status": "valid",
        },
        {
            "rowNumber": 3,
            "email": "jose@example.com",
            "courseId": "hipaa-2026",
            "status": "valid",
        },
    ],
}
# `dev#/components/schemas/Operation`, as a commit returns it (202).
OPERATION_JSON: dict[str, Any] = {
    "name": "op_01JD8H",
    "kind": "enrollments.import",
    "done": False,
}


@pytest.fixture
def api() -> FakeApi:
    fake = FakeApi()
    fake.on("POST", "/auth/token", Reply(json=token_json()))
    return fake


@pytest.fixture
def roster(tmp_path: Path) -> Path:
    path = tmp_path / "roster.csv"
    path.write_bytes(CSV)
    return path


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


def parts_of(request: httpx.Request) -> dict[str, Message]:
    """The multipart parts by name, parsed the way a server would."""
    message = message_from_bytes(
        b"Content-Type: "
        + request.headers["content-type"].encode()
        + b"\r\n\r\n"
        + request.content
    )
    assert message.is_multipart()
    parts: dict[str, Message] = {}
    for part in message.get_payload():
        assert isinstance(part, Message)
        name = part.get_param("name", header="content-disposition")
        assert isinstance(name, str)
        parts[name] = part
    return parts


def payload(part: Message) -> bytes:
    content = part.get_payload(decode=True)
    assert isinstance(content, bytes)
    return content


def test_a_preview_sends_a_csv_part_and_a_json_options_part(api: FakeApi) -> None:
    api.on("POST", PATH, Reply(json=PREVIEW_JSON))

    preview = make_client(api).enrollments.preview_import(
        file=CSV, options={"course_id": "hipaa-2026"}
    )

    assert preview.total_rows == 2
    assert [row.email for row in preview.rows] == [
        "ana@example.com",
        "jose@example.com",
    ]
    [request] = api.requests_to("POST", PATH)
    parts = parts_of(request)
    assert list(parts) == ["file", "options"]
    assert parts["file"].get_content_type() == "text/csv"
    assert parts["file"].get_filename() == "file.csv"
    assert payload(parts["file"]) == CSV
    assert parts["options"].get_content_type() == "application/json"
    assert json.loads(payload(parts["options"])) == {
        "courseId": "hipaa-2026",
        "validateOnly": True,
    }


SOURCES: list[tuple[str, Callable[[Path], FileInput], str]] = [
    ("a path string", str, "roster.csv"),
    ("a pathlib.Path", lambda path: path, "roster.csv"),
    ("bytes", lambda _: CSV, "file.csv"),
    ("an in-memory file", lambda _: io.BytesIO(CSV), "file.csv"),
]


@pytest.mark.parametrize(
    ("source", "filename"),
    [(make, filename) for _, make, filename in SOURCES],
    ids=[name for name, _, _ in SOURCES],
)
def test_an_import_sends_the_bytes_unchanged_with_an_idempotency_key(
    api: FakeApi,
    roster: Path,
    source: Callable[[Path], FileInput],
    filename: str,
) -> None:
    api.on("POST", PATH, Reply(status=202, json=OPERATION_JSON))

    operation = make_client(api).enrollments.import_(file=source(roster))

    assert (operation.name, operation.done) == ("op_01JD8H", False)
    [request] = api.requests_to("POST", PATH)
    assert UUID_V4.match(request.headers["idempotency-key"])
    parts = parts_of(request)
    assert parts["file"].get_filename() == filename
    assert parts["file"].get_content_type() == "text/csv"
    assert payload(parts["file"]) == CSV
    assert json.loads(payload(parts["options"])) == {"validateOnly": False}


def test_an_open_file_is_sent_under_its_own_name(api: FakeApi, roster: Path) -> None:
    api.on("POST", PATH, Reply(status=202, json=OPERATION_JSON))

    with roster.open("rb") as file:
        make_client(api).enrollments.import_(file=file)

    [request] = api.requests_to("POST", PATH)
    parts = parts_of(request)
    assert parts["file"].get_filename() == "roster.csv"
    assert payload(parts["file"]) == CSV


def test_a_retried_import_resends_identical_bytes_under_the_same_key(
    api: FakeApi,
) -> None:
    api.on("POST", PATH, problem(503, "temporarily_unavailable"))
    api.on("POST", PATH, Reply(status=202, json=OPERATION_JSON))

    # A stream can be read only once, so this shows the file is read per call.
    make_client(api).enrollments.import_(file=io.BytesIO(CSV))

    first, retry = api.requests_to("POST", PATH)
    assert retry.headers["idempotency-key"] == first.headers["idempotency-key"]
    assert payload(parts_of(first)["file"]) == CSV
    assert payload(parts_of(retry)["file"]) == CSV


def test_csv_text_passed_as_a_path_is_refused_before_sending(api: FakeApi) -> None:
    with pytest.raises(ValueError, match="path"):
        make_client(api).enrollments.preview_import(file=CSV_TEXT)

    assert api.requests_to("POST", PATH) == []


def test_a_file_opened_in_text_mode_is_refused(api: FakeApi, roster: Path) -> None:
    with roster.open() as text_file, pytest.raises(TypeError, match="binary"):
        make_client(api).enrollments.preview_import(
            file=text_file  # type: ignore[arg-type]
        )

    assert api.requests_to("POST", PATH) == []


@pytest.mark.parametrize(
    "source",
    [lambda path: path, str, lambda _: CSV],
    ids=["a pathlib.Path", "a path string", "bytes"],
)
async def test_async_an_import_sends_the_bytes_unchanged(
    api: FakeApi, roster: Path, source: Callable[[Path], FileInput]
) -> None:
    api.on("POST", PATH, Reply(status=202, json=OPERATION_JSON))

    await make_async_client(api).enrollments.import_(file=source(roster))

    [request] = api.requests_to("POST", PATH)
    assert UUID_V4.match(request.headers["idempotency-key"])
    assert payload(parts_of(request)["file"]) == CSV


async def test_async_csv_text_passed_as_a_path_is_refused(api: FakeApi) -> None:
    with pytest.raises(ValueError, match="path"):
        await make_async_client(api).enrollments.import_(file=CSV_TEXT)

    assert api.requests_to("POST", PATH) == []
