"""Runs a Prism mock of the vendored developer spec for the contract suite.

Prism serves static responses built from the spec's schemas and examples.
Neither `--errors` nor `--dynamic` is used: both make Prism fail on its own
generated responses (static strings ignore `pattern`; dynamic numbers break
OpenAPI 3.1 `exclusiveMinimum`), which says nothing about the SDK. Prism
still answers a request that breaks the spec with a 4xx, which the SDK
raises, and names each broken rule in the `sl-violations` header, which
`violations` collects so a test fails on any of them.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = "openapi/openapi.developer.json"
PRISM = "@stoplight/prism-cli@5.16.0"
# The first run downloads Prism through npx.
STARTUP_TIMEOUT = 180.0


def _free_port() -> int:
    # Releasing the port before Prism binds it is racy in theory, but Prism
    # binds within moments and the suite owns the machine in CI.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
        return port


@pytest.fixture(scope="session")
def prism_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    npx = shutil.which("npx")
    if npx is None:
        pytest.fail("the contract suite needs Node.js: npx is not on PATH")
    port = _free_port()
    log_path = tmp_path_factory.mktemp("prism") / "prism.log"
    with log_path.open("wb") as log:
        # Prism's arguments are fixed here, never taken from input.
        prism = subprocess.Popen(  # noqa: S603
            [npx, "--yes", PRISM, "mock", SPEC, "-h", "127.0.0.1", "-p", str(port)],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            # npx runs Prism as a grandchild; a session of its own lets
            # teardown stop the whole tree.
            start_new_session=True,
        )
    try:
        deadline = time.monotonic() + STARTUP_TIMEOUT
        while "Prism is listening" not in log_path.read_text(errors="replace"):
            if prism.poll() is not None:
                pytest.fail(f"Prism exited:\n{log_path.read_text(errors='replace')}")
            if time.monotonic() > deadline:
                pytest.fail(
                    f"Prism did not start:\n{log_path.read_text(errors='replace')}"
                )
            time.sleep(0.2)
        # Prism serves the spec's paths without the server's `/v1` prefix.
        yield f"http://127.0.0.1:{port}"
    finally:
        os.killpg(prism.pid, signal.SIGTERM)
        prism.wait(timeout=30)


class Violations:
    """Request violations Prism reported, as `METHOD url: location message`.
    Violations in Prism's own generated responses are left out: they come
    from its example generator, not from anything the SDK sent."""

    def __init__(self) -> None:
        self.found: list[str] = []

    def record(self, response: httpx.Response) -> None:
        header = response.headers.get("sl-violations")
        if header is None:
            return
        request = response.request
        self.found.extend(
            f"{request.method} {request.url}: "
            f"{'.'.join(map(str, violation['location']))} {violation['message']}"
            for violation in json.loads(header)
            if violation["location"][:1] == ["request"]
        )

    async def arecord(self, response: httpx.Response) -> None:
        self.record(response)


@pytest.fixture
def violations() -> Iterator[Violations]:
    found = Violations()
    yield found
    assert found.found == [], "Prism reported request violations"
