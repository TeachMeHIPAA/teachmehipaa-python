"""Keeps the README and `docs/reference/code-samples.json` honest.

Every Python sample in `README.md` is type-checked with mypy against the
package, then run against `FakeApi` with what it printed and sent checked.
Each ```python block must follow a `<!-- sample: <id> -->` line, with unique
ids. A sample that uses `client` without creating one gets the Quickstart's
client prepended, bound to an Organization so no lookup is scripted. The
generated code samples are type-checked and linted. Relative links in the
docs must resolve, anchors included.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

import mypy.api
import pytest

import teachmehipaa
from teachmehipaa import (
    AsyncTeachMeHipaa,
    TeachMeHipaa,
)
from tests.fake_api import (
    CLIENT_ID,
    CLIENT_SECRET,
    LEARNER_JSON,
    ORG_ID,
    FakeApi,
    FakeAsyncSleep,
    FakeSleep,
    Reply,
    introspection_json,
    token_json,
)
from tests.test_generated_surface import EXPECTED_METHODS

ROOT = Path(__file__).resolve().parents[1]
DOCS = [ROOT / "README.md"]
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


def _source(sample: Sample) -> str:
    uses_client = re.search(r"\bclient\.", sample.code) is not None
    creates_client = re.search(r"\bclient = |\bas client\b", sample.code) is not None
    return (PRELUDE if uses_client and not creates_client else "") + sample.code


@dataclass
class Harness:
    api: FakeApi
    sleep: FakeSleep
    capsys: pytest.CaptureFixture[str]

    def run(self, sample_id: str) -> dict[str, Any]:
        namespace: dict[str, Any] = {
            "__name__": f"readme_{sample_id.replace('-', '_')}",
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
    }.items():
        monkeypatch.setenv(name, value)
    return Harness(api, sleep, capsys)


def page(items: list[Any], next_cursor: str | None = None) -> Reply:
    return Reply(json={"items": items, "nextCursor": next_cursor})


def test_every_python_sample_is_tagged_once_and_run() -> None:
    ids = [sample.id for sample in _samples()]

    assert len(ids) == len(set(ids))
    assert sorted(ids) == sorted(RUNS)


def test_every_sample_type_checks_against_the_package(tmp_path: Path) -> None:
    files = []
    for sample in SAMPLES.values():
        path = tmp_path / f"readme_{sample.id.replace('-', '_')}.py"
        path.write_text(_source(sample))
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
    h.api.on("GET", f"{ORG}/learners", page([LEARNER]))

    h.run("quickstart")

    assert h.printed() == ["ana@example.com"]
    assert h.api.requests[0].url == "https://sandbox.api.tme.so/v1/auth/token"
    [listing] = h.api.requests_to("GET", f"{ORG}/learners")
    assert dict(listing.url.params) == {"status": "in_progress", "limit": "20"}


#
# `scripts/generate.py` writes one sample per operation to
# `docs/reference/code-samples.json`, for the API reference's language
# picker. They name real credentials and ids, so they are type-checked and
# linted here but never run.

CODE_SAMPLES = ROOT / "docs" / "reference" / "code-samples.json"


def _code_samples() -> dict[str, str]:
    samples: dict[str, str] = json.loads(CODE_SAMPLES.read_text())["samples"]
    return samples


def test_code_samples_cover_every_operation() -> None:
    document = json.loads(CODE_SAMPLES.read_text())
    ir = json.loads((ROOT / "openapi" / "sdk-ir.json").read_text())
    operations = {
        method["operationId"]
        for resource in ir["resources"]
        for method in resource["methods"]
    }

    assert document["language"] == "python"
    assert document["release"] == (ROOT / "OPENAPI_VERSION").read_text().strip()
    assert sorted(document["samples"]) == sorted(operations)


def _client_calls(code: str) -> set[str]:
    """`resource.method` for every `client.<resource>.<method>(...)` call."""
    calls = set()
    for node in ast.walk(ast.parse(code)):
        if not isinstance(node, ast.Call):
            continue
        parts: list[str] = []
        target = node.func
        while isinstance(target, ast.Attribute):
            parts.insert(0, target.attr)
            target = target.value
        if isinstance(target, ast.Name) and target.id == "client" and parts:
            calls.add(".".join(parts))
    return calls


@pytest.mark.parametrize("operation", sorted(_code_samples()))
def test_code_sample_calls_its_operation(operation: str) -> None:
    code = _code_samples()[operation]
    # Where two methods share an operationId, the sample shows the first.
    method = EXPECTED_METHODS[operation][0]

    assert method in _client_calls(code)
    assert 'environment="sandbox"' in code


def test_code_samples_type_check_and_lint(tmp_path: Path) -> None:
    files = []
    for operation, code in _code_samples().items():
        path = tmp_path / f"sample_{operation}.py"
        path.write_text(code)
        files.append(str(path))

    config = str(ROOT / "pyproject.toml")
    stdout, stderr, status = mypy.api.run(["--config-file", config, *files])
    lint = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--no-cache",
            "--config",
            config,
            *files,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert status == 0, stdout + stderr
    assert lint.returncode == 0, lint.stdout + lint.stderr


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
