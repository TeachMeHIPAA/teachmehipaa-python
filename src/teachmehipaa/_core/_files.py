"""Files a caller uploads, such as an Enrollment import CSV."""

from __future__ import annotations

import mimetypes
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import IO, TYPE_CHECKING, TypeAlias, cast

if TYPE_CHECKING:
    from ._request import ApiRequest

FileInput: TypeAlias = str | os.PathLike[str] | bytes | IO[bytes]
"""A path to read, the file's bytes, or a file opened in binary mode. A `str`
is always a path: pass CSV text as bytes (`text.encode()`)."""


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
                cast(FileInput, body[name]), name, default_name=name + extension
            )
    return replace(api_request, body=body)


def _read(file: FileInput, argument: str, *, default_name: str) -> Upload:
    if isinstance(file, bytes):
        return Upload(default_name, file)
    if isinstance(file, str) and ("\n" in file or "\r" in file):
        # A path never holds a line break; CSV text always does.
        raise ValueError(
            f"{argument} was given text, but a str is a file path. Pass the "
            "content as bytes instead, such as `csv_text.encode()`."
        )
    if isinstance(file, str | os.PathLike):
        path = Path(file)
        return Upload(path.name, path.read_bytes())
    content = file.read()
    if not isinstance(content, bytes):
        raise TypeError(f"{argument} must be opened in binary mode ('rb')")
    name = getattr(file, "name", None)
    return Upload(Path(name).name if isinstance(name, str) else default_name, content)
