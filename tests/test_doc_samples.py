"""Keeps the README and the guides honest: every Python sample is
type-checked with mypy against the package, then run against `FakeApi` with
what it printed and sent checked.

Each ```python block in `README.md` and `docs/guides/*.md` must follow a
`<!-- sample: <id> -->` line, with ids unique across all of them. A sample
that uses `client` without creating one gets the Quickstart's client
prepended, bound to an Organization so no lookup is scripted. Samples name
the caller's own storage and secrets (`cursors`, `shutdown`,
`signing_secrets`, `access_token`); `PLACEHOLDERS` types them and `Storage`
stands in for them at run time. Relative links in the docs must resolve,
anchors included.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import threading
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

import httpx
import mypy.api
import pytest
from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory
from fastapi import FastAPI
from flask import Flask

import teachmehipaa
from teachmehipaa import (
    AsyncTeachMeHipaa,
    NotFoundError,
    TeachMeHipaa,
    Webhook,
)
from tests.fake_api import (
    CLIENT_ID,
    CLIENT_SECRET,
    LEARNER_JSON,
    ORG_ID,
    REQUEST_ID,
    FakeApi,
    FakeAsyncSleep,
    FakeSleep,
    Reply,
    introspection_json,
    problem,
    token_json,
)

ROOT = Path(__file__).resolve().parents[1]
DOCS = [ROOT / "README.md", *sorted((ROOT / "docs" / "guides").glob("*.md"))]
WEBHOOK_SECRET = "readme-test-signing-secret"
ORG = f"/organizations/{ORG_ID}"
LEARNER_ID = "sub_01JD80AB2C3D4E5F6G7H8J9K0M"
LEARNER = {**LEARNER_JSON, "learnerId": LEARNER_ID}


class Sample(NamedTuple):
    id: str
    code: str
    doc: str


def _samples() -> list[Sample]:
    found = []
    for path in DOCS:
        doc = str(path.relative_to(ROOT))
        text = path.read_text()
        blocks = re.findall(r"^([^\n]*)\n```python\n(.*?)^```$", text, re.M | re.S)
        for tag_line, code in blocks:
            tag = re.fullmatch(r"<!-- sample: ([\w-]+) -->", tag_line)
            if tag is None:
                raise AssertionError(
                    f"{doc}: a python block has no sample tag:\n{code}"
                )
            found.append(Sample(tag.group(1), code, doc))
    return found


SAMPLES = {sample.id: sample for sample in _samples()}

PRELUDE = f"""\
import os as _os
from teachmehipaa import TeachMeHipaa as _TeachMeHipaa
client = _TeachMeHipaa(
    client_id=_os.environ["TMH_CLIENT_ID"],
    client_secret=_os.environ["TMH_CLIENT_SECRET"],
    environment="sandbox",
    organization_id="{ORG_ID}",
)
"""

PLACEHOLDERS = """\
import threading

class Cursors:
    def load(self) -> str | None: ...
    def save(self, event_id: str | None) -> None: ...

class SigningSecrets:
    def save(self, subscription_id: str, secret: str) -> None: ...

cursors: Cursors
shutdown: threading.Event
signing_secrets: SigningSecrets
access_token: str
"""
PLACEHOLDER_NAMES = "cursors, shutdown, signing_secrets, access_token"


def _source(sample: Sample) -> str:
    uses_client = re.search(r"\bclient\.", sample.code) is not None
    creates_client = re.search(r"\bclient = |\bas client\b", sample.code) is not None
    return (PRELUDE if uses_client and not creates_client else "") + sample.code


STATIC_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiJ9.static.sig"


@dataclass
class Storage:
    """Run-time stand-ins for the storage the samples name."""

    cursor: str | None = None
    saved_cursors: list[str | None] = field(default_factory=list)
    shutdown: threading.Event = field(default_factory=threading.Event)
    saved_secrets: list[tuple[str, str]] = field(default_factory=list)

    def namespace(self) -> dict[str, object]:
        storage = self

        class Cursors:
            def load(self) -> str | None:
                return storage.cursor

            def save(self, event_id: str | None) -> None:
                storage.saved_cursors.append(event_id)

        class SigningSecrets:
            def save(self, subscription_id: str, secret: str) -> None:
                storage.saved_secrets.append((subscription_id, secret))

        return {
            "cursors": Cursors(),
            "shutdown": self.shutdown,
            "signing_secrets": SigningSecrets(),
            "access_token": STATIC_ACCESS_TOKEN,
        }


@dataclass
class Harness:
    api: FakeApi
    storage: Storage
    sleep: FakeSleep
    capsys: pytest.CaptureFixture[str]

    def run(self, sample_id: str) -> dict[str, Any]:
        namespace: dict[str, Any] = {
            "__name__": f"readme_{sample_id.replace('-', '_')}",
            **self.storage.namespace(),
        }
        sample = SAMPLES[sample_id]
        code = compile(_source(sample), f"{sample.doc}:{sample_id}", "exec")
        # The docs are this repository's own files, not outside input.
        exec(code, namespace)  # noqa: S102
        return namespace

    def printed(self) -> list[str]:
        return self.capsys.readouterr().out.splitlines()


@pytest.fixture
def harness(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> Harness:
    """Points every client the samples create at the fake, unless the sample
    brings its own `http_client`, with no real waits, and runs samples in a
    temporary directory, since the file samples read and write relative
    paths."""
    monkeypatch.chdir(tmp_path)
    api = FakeApi()
    api.on("POST", "/auth/token", Reply(json=token_json()))
    sleep = FakeSleep()
    async_sleep = FakeAsyncSleep()

    class FakedTeachMeHipaa(TeachMeHipaa):
        def __init__(self, **options: Any) -> None:
            super().__init__(
                **{"http_client": api.sync_client(), **options, "sleep": sleep}
            )

    class FakedAsyncTeachMeHipaa(AsyncTeachMeHipaa):
        def __init__(self, **options: Any) -> None:
            super().__init__(
                **{"http_client": api.async_client(), **options, "sleep": async_sleep}
            )

    monkeypatch.setattr(teachmehipaa, "TeachMeHipaa", FakedTeachMeHipaa)
    monkeypatch.setattr(teachmehipaa, "AsyncTeachMeHipaa", FakedAsyncTeachMeHipaa)
    for name, value in {
        "TMH_CLIENT_ID": CLIENT_ID,
        "TMH_CLIENT_SECRET": CLIENT_SECRET,
        "TMH_WEBHOOK_SECRET": WEBHOOK_SECRET,
    }.items():
        monkeypatch.setenv(name, value)
    return Harness(api, Storage(), sleep, capsys)


def page(items: list[Any], next_cursor: str | None = None) -> Reply:
    return Reply(json={"items": items, "nextCursor": next_cursor})


def body(request: httpx.Request) -> Any:
    return json.loads(request.content)


def enrollment(n: int) -> dict[str, Any]:
    """`dev#/components/schemas/Enrollment`."""
    return {
        "enrollmentId": f"{LEARNER_ID}__hipaa-2026-{n}",
        "subjectId": LEARNER_ID,
        "courseId": "hipaa-2026",
        "orgId": ORG_ID,
        "status": "INVITED",
        "effectiveStatus": "INVITED",
        "archived": False,
        "cycle": 1,
        "rev": 1,
        "invitedAt": "2026-11-15T09:00:00.000Z",
        "startedAt": None,
        "completedAt": None,
        "certifiedAt": None,
        "expiresAt": None,
        "certificateId": None,
    }


COMPLIANCE = {
    "asOf": "2026-11-15T12:00:00.000Z",
    "courseId": "hipaa-2026",
    "totals": {
        "learners": 4,
        "compliant": 3,
        "expiringSoon": 1,
        "expired": 0,
        "inProgress": 1,
        "notStarted": 0,
        "inviteBounced": 0,
    },
    "compliantRate": 0.75,
}

COURSE = {
    "courseId": "hipaa-2026",
    "title": "HIPAA Essentials 2026",
    "courseVersion": "2026.1",
    "passingThreshold": 0.8,
}


OPERATION_NAME = f"organizations/{ORG_ID}/operations/0b7d4a8e-5c1f-4e2a-9d3b"


def operation(kind: str, response: Any = None) -> dict[str, Any]:
    """A done `dev#/components/schemas/Operation`."""
    return {
        "name": OPERATION_NAME,
        "done": True,
        "metadata": {"kind": kind},
        "response": response,
    }


def event(event_id: str) -> dict[str, Any]:
    """A `learner.certified` Event, as the log and Deliveries carry it."""
    return {
        "eventId": event_id,
        "eventType": "learner.certified",
        "orgId": ORG_ID,
        "occurredAt": "2026-11-15T12:00:00.000Z",
        "data": {
            "learnerId": LEARNER_ID,
            "email": "ana@example.com",
            "externalId": "hr-123",
            "courseId": "hipaa-2026",
            "status": "certified",
            "occurredAt": "2026-11-15T12:00:00.000Z",
        },
    }


def test_every_doc_is_checked() -> None:
    guides = {path.name for path in DOCS if path.parent.name == "guides"}

    assert {"getting-started.md", "webhooks.md", "testing.md"} <= guides


def test_every_python_sample_is_tagged_once_and_run() -> None:
    ids = [sample.id for sample in _samples()]

    assert len(ids) == len(set(ids))
    assert sorted(ids) == sorted(RUNS)


def test_every_sample_type_checks_against_the_package(tmp_path: Path) -> None:
    (tmp_path / "readme_placeholders.pyi").write_text(PLACEHOLDERS)
    files = []
    for sample in SAMPLES.values():
        path = tmp_path / f"readme_{sample.id.replace('-', '_')}.py"
        imports = f"from readme_placeholders import {PLACEHOLDER_NAMES}\n"
        path.write_text(imports + _source(sample))
        files.append(str(path))

    stdout, stderr, status = mypy.api.run(
        ["--config-file", str(ROOT / "pyproject.toml"), *files]
    )

    assert status == 0, stdout + stderr


RUNS: dict[str, Callable[[Harness], None]] = {}


def runs(sample_id: str) -> Callable[[Callable[[Harness], None]], None]:
    def register(check: Callable[[Harness], None]) -> None:
        RUNS[sample_id] = check

    return register


@pytest.mark.parametrize("sample_id", sorted(SAMPLES))
def test_sample_runs(sample_id: str, harness: Harness) -> None:
    RUNS[sample_id](harness)


@runs("quickstart")
def _quickstart(h: Harness) -> None:
    h.api.on("GET", "/auth/introspection", Reply(json=introspection_json()))
    h.api.on("GET", f"{ORG}/learners/{LEARNER_ID}", Reply(json=LEARNER))
    h.api.on("GET", f"{ORG}/learners", page([LEARNER]))

    h.run("quickstart")

    assert h.printed() == ["Ana Lima in_progress", "ana@example.com"]
    assert h.api.requests[0].url == "https://api-teachmehipaa-dev.web.app/v1/auth/token"
    [listing] = h.api.requests_to("GET", f"{ORG}/learners")
    assert dict(listing.url.params) == {"status": "in_progress", "limit": "20"}


@runs("organization")
def _organization(h: Harness) -> None:
    h.api.on(
        "GET",
        f"{ORG}/compliance",
        Reply(json=COMPLIANCE, headers={"x-request-id": REQUEST_ID}),
    )

    h.run("organization")

    assert h.api.requests_to("GET", "/auth/introspection") == []
    assert h.printed() == [f"0.75 {REQUEST_ID}"]


@runs("public-lookups")
def _public_lookups(h: Harness) -> None:
    h.api.on(
        "GET",
        "/certificate-verifications/aB3dE9",
        Reply(
            json={
                "status": "valid",
                "learnerName": "Ana Lima",
                "courseTitle": "HIPAA Essentials 2026",
                "issuedAt": "2026-11-02T10:30:00.000Z",
                "expiresAt": "2027-11-02T10:30:00.000Z",
                "issuer": "TeachMeHIPAA",
            }
        ),
    )
    h.api.on("GET", "/courses", page([COURSE]))

    h.run("public-lookups")

    assert h.printed() == ["valid Ana Lima", "HIPAA Essentials 2026"]
    assert h.api.requests_to("POST", "/auth/token") == []
    assert all("authorization" not in r.headers for r in h.api.requests)


@runs("learner-writes")
def _learner_writes(h: Harness) -> None:
    h.api.on("POST", f"{ORG}/learners", Reply(status=201, json=LEARNER))
    h.api.on("PUT", f"{ORG}/learners/by-external-id/hr-123", Reply(json=LEARNER))

    h.run("learner-writes")

    assert h.printed() == ["invited", LEARNER_ID]
    [upsert] = h.api.requests_to("PUT", f"{ORG}/learners/by-external-id/hr-123")
    assert body(upsert) == {"email": "ana@example.com", "name": "Ana Example"}


@runs("pagination")
def _pagination(h: Harness) -> None:
    second = {**LEARNER, "learnerId": "sub_01JD80AB2C3D4E5F6G7H8J9K0N"}
    h.api.on("GET", f"{ORG}/learners", page([LEARNER], "cursor-2"))
    h.api.on("GET", f"{ORG}/learners", page([second]))
    h.api.on("GET", f"{ORG}/enrollments", page([enrollment(1)], "cursor-e2"))
    h.api.on("GET", f"{ORG}/enrollments", page([enrollment(2), enrollment(3)]))

    h.run("pagination")

    assert h.printed() == [LEARNER_ID, second["learnerId"], "1", "2"]
    later = h.api.requests_to("GET", f"{ORG}/learners")[1]
    assert dict(later.url.params) == {"limit": "100", "cursor": "cursor-2"}


@runs("errors")
def _errors(h: Harness) -> None:
    h.api.on(
        "GET",
        f"{ORG}/learners/{LEARNER_ID}",
        problem(404, "not_found", detail="No learner with that id."),
    )

    h.run("errors")

    assert h.printed() == ["No such Learner"]


@runs("request-options")
def _request_options(h: Harness) -> None:
    h.api.on("POST", f"{ORG}/enrollments", problem(503, "unavailable"))
    h.api.on(
        "POST",
        f"{ORG}/enrollments",
        Reply(status=201, json=enrollment(1), headers={"x-request-id": "req_e1"}),
    )

    h.run("request-options")

    attempts = h.api.requests_to("POST", f"{ORG}/enrollments")
    assert [r.headers["idempotency-key"] for r in attempts] == [
        "hr-sync-2026-11-15-ana",
        "hr-sync-2026-11-15-ana",
    ]
    assert attempts[0].extensions["timeout"]["read"] == 10.0
    assert [r.headers["x-request-id"] for r in attempts] == [
        "hr-sync-2026-11-15-ana",
        "hr-sync-2026-11-15-ana",
    ]
    assert len(h.sleep.waits) == 1
    assert h.printed() == [f"{LEARNER_ID}__hipaa-2026-1 req_e1"]


@runs("conditional-write")
def _conditional_write(h: Harness) -> None:
    learner_path = f"{ORG}/learners/{LEARNER_ID}"
    h.api.on("GET", learner_path, Reply(json=LEARNER, headers={"etag": '"7"'}))
    h.api.on("PATCH", learner_path, problem(412, "precondition_failed"))

    h.run("conditional-write")

    [update] = h.api.requests_to("PATCH", learner_path)
    assert update.headers["if-match"] == '"7"'
    assert update.headers["content-type"] == "application/merge-patch+json"
    assert body(update) == {"name": "Ana Q. Example", "externalId": None}
    assert h.printed() == ["Someone else changed this Learner; read it again"]


@runs("not-modified")
def _not_modified(h: Harness) -> None:
    h.api.on("GET", "/courses/hipaa-2026", Reply(json=COURSE, headers={"etag": '"c1"'}))
    h.api.on("GET", "/courses/hipaa-2026", Reply(status=304, text=""))

    h.run("not-modified")

    second = h.api.requests_to("GET", "/courses/hipaa-2026")[1]
    assert second.headers["if-none-match"] == '"c1"'
    assert h.printed() == ["still current", "HIPAA Essentials 2026"]


# base64 of "learnerId,email\r\nsub_01,ana@example.com\r\n"
EXPORTED_CSV_BASE64 = "bGVhcm5lcklkLGVtYWlsDQpzdWJfMDEsYW5hQGV4YW1wbGUuY29tDQo="


@runs("operations")
def _operations(h: Harness) -> None:
    h.api.on(
        "POST",
        f"{ORG}/learners:export",
        Reply(
            status=202,
            json=operation(
                "learners:export",
                {
                    "format": "csv",
                    "contentType": "text/csv; charset=utf-8",
                    "filename": f"learners-{ORG_ID}.csv",
                    "rowCount": 1,
                    "dataBase64": EXPORTED_CSV_BASE64,
                },
            ),
        ),
    )

    h.run("operations")

    csv = "learnerId,email\r\nsub_01,ana@example.com\r\n"
    assert h.printed() == [f"learners-{ORG_ID}.csv 1 {len(csv)}"]


ROSTER_CSV = b"email,name\r\nana@example.com,Ana Example\r\n"


@runs("csv-import")
def _csv_import(h: Harness) -> None:
    (Path.cwd() / "roster.csv").write_bytes(ROSTER_CSV)
    preview = {
        "totalRows": 1,
        "validRows": 1,
        "seatsRequired": 1,
        "seatsAvailable": 9,
        "rows": [
            {
                "rowNumber": 1,
                "email": "ana@example.com",
                "courseId": "hipaa-2026",
                "status": "ok",
            }
        ],
    }
    h.api.on("POST", f"{ORG}/enrollments:import", Reply(json=preview))
    h.api.on(
        "POST",
        f"{ORG}/enrollments:import",
        Reply(status=202, json=operation("enrollments:import")),
    )

    h.run("csv-import")

    assert h.printed() == ["1 of 1 rows are valid"]
    imports = h.api.requests_to("POST", f"{ORG}/enrollments:import")
    assert len(imports) == 2
    assert all(ROSTER_CSV in request.content for request in imports)


@runs("pdf-download")
def _pdf_download(h: Harness) -> None:
    pdf = b"%PDF-1.7 certificate"
    h.api.on(
        "GET",
        f"{ORG}/certificates/cert_01JD8F/content",
        Reply(
            content=pdf,
            content_type="application/pdf",
            headers={"content-disposition": 'attachment; filename="ana.pdf"'},
        ),
    )

    h.run("pdf-download")

    work = Path.cwd()
    assert (work / "ana.pdf").read_bytes() == pdf
    assert (work / "certificate-copy.pdf").read_bytes() == pdf


def _signed(path: str, payload: bytes) -> dict[str, str]:
    return Webhook.generate_test_headers(payload, WEBHOOK_SECRET, path)


DELIVERY = json.dumps(event("evt_01JD8M")).encode()
TAMPERED = DELIVERY.replace(b"learner.certified", b"learner.removed")


def _webhook_outcomes(post: Callable[[str, bytes, dict[str, str]], Any]) -> None:
    """A Delivery verifies on the exact path it was signed for, with or
    without a query string, and fails on a changed body or another path."""
    for path in ("/webhooks/tmh", "/webhooks/tmh?tenant=acme"):
        assert post(path, DELIVERY, _signed(path, DELIVERY)) == (
            200,
            "received learner.certified",
        )
    headers = _signed("/webhooks/tmh", DELIVERY)
    assert post("/webhooks/tmh", TAMPERED, headers) == (400, "body_hash_mismatch")
    assert post("/webhooks/tmh?tenant=acme", DELIVERY, headers) == (
        400,
        "signature_mismatch",
    )


@runs("webhook-flask")
def _webhook_flask(h: Harness) -> None:
    app = h.run("webhook-flask")["app"]
    assert isinstance(app, Flask)
    test_client = app.test_client()

    def post(path: str, payload: bytes, headers: dict[str, str]) -> Any:
        response = test_client.post(path, data=payload, headers=headers)
        return response.status_code, response.get_data(as_text=True)

    _webhook_outcomes(post)


@runs("webhook-fastapi")
def _webhook_fastapi(h: Harness) -> None:
    app = h.run("webhook-fastapi")["app"]
    assert isinstance(app, FastAPI)

    async def send(path: str, payload: bytes, headers: dict[str, str]) -> Any:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as asgi_client:
            response = await asgi_client.post(path, content=payload, headers=headers)
        return response.status_code, response.text

    def post(path: str, payload: bytes, headers: dict[str, str]) -> Any:
        return asyncio.run(send(path, payload, headers))

    _webhook_outcomes(post)


@runs("webhook-django")
def _webhook_django(h: Harness) -> None:
    if not settings.configured:
        settings.configure()
    view = h.run("webhook-django")["tmh_webhook"]
    factory = RequestFactory()

    def post(path: str, payload: bytes, headers: dict[str, str]) -> Any:
        request = factory.post(
            path, data=payload, content_type="application/json", headers=headers
        )
        response = view(request)
        assert isinstance(response, HttpResponse)
        return response.status_code, response.content.decode()

    _webhook_outcomes(post)


@runs("webhook-test-headers")
def _webhook_test_headers(h: Harness) -> None:
    h.run("webhook-test-headers")

    assert h.printed() == ["learner.certified"]


@runs("events-tail")
def _events_tail(h: Harness) -> None:
    h.storage.cursor = "evt_01"

    def caught_up(request: httpx.Request) -> Reply:
        # How a real service ends the tail: it sets `shutdown` on its way out.
        h.storage.shutdown.set()
        return page([])

    h.api.on("GET", f"{ORG}/events", page([event("evt_02"), event("evt_03")]))
    h.api.on("GET", f"{ORG}/events", caught_up)

    h.run("events-tail")

    polls = h.api.requests_to("GET", f"{ORG}/events")
    assert [poll.url.params["after"] for poll in polls] == ["evt_01", "evt_03"]
    assert h.storage.saved_cursors == ["evt_02", "evt_03"]
    assert h.printed() == ["learner.certified evt_02", "learner.certified evt_03"]


@runs("async")
def _async(h: Harness) -> None:
    h.api.on("GET", "/auth/introspection", Reply(json=introspection_json()))
    h.api.on("GET", f"{ORG}/learners/{LEARNER_ID}", Reply(json=LEARNER))
    h.api.on("GET", f"{ORG}/compliance", Reply(json=COMPLIANCE))
    h.api.on("GET", f"{ORG}/learners", page([LEARNER]))

    h.run("async")

    assert h.printed() == ["Ana Lima 0.75", "ana@example.com"]
    assert len(h.api.requests_to("POST", "/auth/token")) == 1
    assert len(h.api.requests_to("GET", "/auth/introspection")) == 1


@runs("configuration")
def _configuration(h: Harness) -> None:
    h.run("configuration")

    assert h.printed() == ["sandbox https://api-teachmehipaa-dev.web.app/v1 3"]


class Recorder(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@runs("logging")
def _logging(h: Harness) -> None:
    h.api.on(
        "GET",
        f"{ORG}/learners",
        Reply(
            json={"items": [], "nextCursor": None}, headers={"x-request-id": "req_l"}
        ),
    )
    logger = logging.getLogger("teachmehipaa")
    handler = Recorder()
    logger.addHandler(handler)
    try:
        h.run("logging")
    finally:
        logger.removeHandler(handler)
        logger.setLevel(logging.NOTSET)

    messages = [record.getMessage() for record in handler.records]
    assert [re.sub(r"\d+ ms", "N ms", message) for message in messages] == [
        "POST /v1/auth/token 200 in N ms (request id None)",
        f"GET /v1{ORG}/learners 200 in N ms (request id req_l)",
    ]


@runs("first-call")
def _first_call(h: Harness) -> None:
    h.api.on("GET", "/auth/introspection", Reply(json=introspection_json()))
    h.api.on("GET", f"{ORG}/compliance", Reply(json=COMPLIANCE))
    h.api.on("GET", f"{ORG}/learners", page([LEARNER]))

    h.run("first-call")

    assert h.printed() == [
        "75% of Learners are compliant",
        "ana@example.com in_progress",
    ]
    [listing] = h.api.requests_to("GET", f"{ORG}/learners")
    assert dict(listing.url.params) == {"limit": "20"}


@runs("async-pagination")
def _async_pagination(h: Harness) -> None:
    h.api.on("GET", f"{ORG}/learners", page([LEARNER], "cursor-2"))
    h.api.on("GET", f"{ORG}/learners", page([{**LEARNER, "email": "jo@example.com"}]))
    print_emails = h.run("async-pagination")["print_emails"]

    async def main() -> None:
        async with teachmehipaa.AsyncTeachMeHipaa(
            client_id=CLIENT_ID, client_secret=CLIENT_SECRET, organization_id=ORG_ID
        ) as client:
            await print_emails(client)

    asyncio.run(main())

    assert h.printed() == ["ana@example.com", "jo@example.com"]


@runs("client-credentials")
def _client_credentials(h: Harness) -> None:
    h.api.on("GET", "/auth/introspection", Reply(json=introspection_json()))

    h.run("client-credentials")

    [token_request] = h.api.requests_to("POST", "/auth/token")
    form = urllib.parse.parse_qs(token_request.content.decode())
    assert form["scope"] == ["learners:read"]
    assert h.printed() == ["test org_acme ['learners:read', 'learners:write']"]


@runs("static-token")
def _static_token(h: Harness) -> None:
    h.api.on("GET", "/auth/introspection", Reply(json=introspection_json()))
    h.api.on("GET", f"{ORG}/compliance", Reply(json=COMPLIANCE))

    h.run("static-token")

    assert h.printed() == ["0.75"]
    assert h.api.requests_to("POST", "/auth/token") == []
    assert {r.headers["authorization"] for r in h.api.requests} == {
        f"Bearer {STATIC_ACCESS_TOKEN}"
    }


@runs("events-list")
def _events_list(h: Harness) -> None:
    h.api.on("GET", f"{ORG}/events", page([event("evt_02"), event("evt_03")]))

    h.run("events-list")

    [listing] = h.api.requests_to("GET", f"{ORG}/events")
    assert dict(listing.url.params) == {"type": "learner.certified"}
    assert h.printed() == ["ana@example.com 2026-11-15"] * 2


SUBSCRIPTION_ID = "whs_01JD8K2M4N6P8R0T2V4X6Z8B0D"


@runs("webhook-subscription-create")
def _webhook_subscription_create(h: Harness) -> None:
    created = {
        "subscriptionId": SUBSCRIPTION_ID,
        "endpointUrl": "https://hooks.example.com/webhooks/tmh",
        "eventTypes": ["learner.certified", "learner.expiring"],
        "enabled": True,
        "description": "HR sync",
        "seatsLowThreshold": 5,
        "secretKeyId": "key_01",
        "createdAt": "2026-11-15T12:00:00.000Z",
        "rev": 1,
        "secret": "whsec_test",
    }
    h.api.on("POST", f"{ORG}/webhook-subscriptions", Reply(status=201, json=created))

    h.run("webhook-subscription-create")

    [create] = h.api.requests_to("POST", f"{ORG}/webhook-subscriptions")
    assert body(create) == {
        "endpointUrl": "https://hooks.example.com/webhooks/tmh",
        "eventTypes": ["learner.certified", "learner.expiring"],
        "description": "HR sync",
    }
    assert h.storage.saved_secrets == [(SUBSCRIPTION_ID, "whsec_test")]
    assert h.printed() == [f"{SUBSCRIPTION_ID} key_01"]


@runs("webhook-test-delivery")
def _webhook_test_delivery(h: Harness) -> None:
    pending = {"name": OPERATION_NAME, "done": False}
    sent = {**operation("webhookSubscriptions:test"), "response": None}
    sent["response"] = {"_tag": "sent", "responseStatus": 204}
    h.api.on(
        "POST",
        f"{ORG}/webhook-subscriptions/{SUBSCRIPTION_ID}:test",
        Reply(status=202, json=pending),
    )
    poll_path = f"{ORG}/operations/{OPERATION_NAME.rsplit('/', 1)[1]}"
    h.api.on("GET", poll_path, Reply(json=pending))
    h.api.on("GET", poll_path, Reply(json=sent))

    h.run("webhook-test-delivery")

    assert len(h.api.requests_to("GET", poll_path)) == 2
    assert h.printed() == ["endpoint answered 204"]


CERTIFICATES_CSV = "certificateId,email\r\ncert_01JD8F,ana@example.com\r\n"


@runs("certificates-export")
def _certificates_export(h: Harness) -> None:
    h.api.on(
        "POST",
        f"{ORG}/certificates:export",
        Reply(
            status=202,
            json=operation(
                "certificates:export",
                {
                    "format": "csv",
                    "contentType": "text/csv; charset=utf-8",
                    "filename": f"certificates-{ORG_ID}.csv",
                    "rowCount": 1,
                    "dataBase64": base64.b64encode(CERTIFICATES_CSV.encode()).decode(),
                },
            ),
        ),
    )

    h.run("certificates-export")

    [export] = h.api.requests_to("POST", f"{ORG}/certificates:export")
    assert body(export) == {"format": "csv"}
    written = (Path.cwd() / f"certificates-{ORG_ID}.csv").read_bytes()
    assert written == CERTIFICATES_CSV.encode()
    assert h.printed() == ["1 Certificates exported"]


@runs("fake-transport")
def _fake_transport(h: Harness) -> None:
    client = h.run("fake-transport")["client"]

    assert h.printed() == ["0.75"]
    assert h.api.requests == []
    with pytest.raises(NotFoundError) as raised:
        client.learners.list()
    assert raised.value.code == "not_found"


@runs("webhook-handler-test")
def _webhook_handler_test(h: Harness) -> None:
    namespace = h.run("webhook-handler-test")
    tests = [value for name, value in namespace.items() if name.startswith("test_")]

    for test in tests:
        test()

    assert len(tests) == 2


@runs("timeouts")
def _timeouts(h: Harness) -> None:
    h.api.on("GET", f"{ORG}/learners", page([LEARNER]))

    h.run("timeouts")

    [listing] = h.api.requests_to("GET", f"{ORG}/learners")
    assert listing.extensions["timeout"] == {
        "connect": 5.0,
        "read": 30.0,
        "write": 30.0,
        "pool": 30.0,
    }
    assert h.printed() == ["1"]


# A link target, optionally with an anchor, in a Markdown link or image.
LINK = re.compile(r"\]\((?!https?:|mailto:)([^)\s]+)\)")


def _anchors(markdown: str) -> set[str]:
    """GitHub's heading anchors: lowercased, punctuation but `-` and `_`
    dropped, spaces turned into hyphens."""
    headings = re.findall(r"^#{1,6} (.+)$", markdown, re.M)
    return {
        re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")
        for heading in headings
    }


LINKED_DOCS = [
    *DOCS,
    ROOT / "CONTRIBUTING.md",
    ROOT / "docs" / "README.md",
    ROOT / "docs" / "reference" / "resources.md",
    ROOT / "examples" / "README.md",
]


@pytest.mark.parametrize(
    "doc", LINKED_DOCS, ids=[str(p.relative_to(ROOT)) for p in LINKED_DOCS]
)
def test_relative_links_resolve(doc: Path) -> None:
    broken = []
    for target in LINK.findall(doc.read_text()):
        path_part, _, anchor = target.partition("#")
        linked = (doc.parent / path_part).resolve() if path_part else doc
        if not linked.exists() or (
            anchor
            and linked.suffix == ".md"
            and anchor not in _anchors(linked.read_text())
        ):
            broken.append(target)

    assert broken == []
