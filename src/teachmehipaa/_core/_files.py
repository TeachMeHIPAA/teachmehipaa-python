"""Files a caller uploads, such as an Enrollment import CSV."""

from __future__ import annotations

import mimetypes
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import IO, TYPE_CHECKING, TypeAlias, cast

if TYPE_CHECKING:
    from ._request import ApiRequest

FileInput: TypeAlias = bytes | IO[bytes] | os.PathLike[str]
"""A file's bytes, an open binary file, or a path to read."""


@dataclass(frozen=True)
class Upload:
    filename: str
    content: bytes


def read_uploads(api_request: ApiRequest) -> ApiRequest:
    """`api_request` with its file parts read. Files are read once per call,
    not per attempt, so every retry sends the same bytes even from a
    stream."""
    if api_request.body is None or not api_request.binary_parts:
        return api_request
    body = dict(api_request.body)
    for name, content_type in api_request.binary_parts.items():
        if name in body:
            extension = mimetypes.guess_extension(content_type) or ""
            body[name] = _read(
                cast(FileInput, body[name]), default_name=name + extension
            )
    return replace(api_request, body=body)


def _read(file: FileInput, *, default_name: str) -> Upload:
    if isinstance(file, bytes):
        return Upload(default_name, file)
    if isinstance(file, os.PathLike):
        path = Path(file)
        return Upload(path.name, path.read_bytes())
    name = getattr(file, "name", None)
    return Upload(
        Path(name).name if isinstance(name, str) else default_name, file.read()
    )
