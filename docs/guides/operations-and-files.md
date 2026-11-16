# Operations and files

Exports, imports, batch writes, Test deliveries and redrives return an
Operation: work that may finish after the request that started it returns.
This guide covers waiting for Operations, exporting and importing CSV
files, and downloading Certificate PDFs.

Samples assume a `client` created as in
[Getting started](getting-started.md#3-make-your-first-call).

## Waiting for an Operation

Methods that start an Operation return an `Operation` (`AsyncOperation` on
the async client) with a `name`, `done`, and, once done, a `response` or an
`error`. `wait()` polls until it is done, backing off from `interval`
(default 1 s) to 10 s, and returns the finished Operation. It raises
`OperationTimeoutError` after `timeout` (default 300 s), or
`OperationFailedError` if the Operation finished with an error; both carry
the `operation`. An Operation that is already done, as exports always are,
returns without a request.

An export's `export_result()` hands back the CSV file:

<!-- sample: operations -->
```python
operation = client.learners.export(format="csv", course_id="hipaa-2026")
done = operation.wait(timeout=60, interval=2)
export = done.export_result()
print(export.filename, export.row_count, len(export.csv))
```

To check on an Operation later, from another process, keep its `name`:
`operation_id_from_name(operation.name)` gives the id that
`operations.retrieve` takes.

## Exporting Certificates

`certificates.export`, `enrollments.export` and `learners.export` each
produce one CSV file (RFC 4180, CRLF line endings) in `export.csv`. Write it
with `newline=""` so the line endings stay as they are:

<!-- sample: certificates-export -->
```python
from pathlib import Path

export = client.certificates.export(format="csv").wait().export_result()
Path(export.filename or "certificates.csv").write_text(export.csv, newline="")
print(export.row_count, "Certificates exported")
```

An export too large for one file fails with an `InvalidRequestError` whose
`code` is `export_too_large`. `learners.export` covers one Course, and can
be narrowed further to one `status`.

## Importing Enrollments from a CSV file

A CSV file with an `email` column, and optionally `name` and `courseId`,
can enroll up to 500 people at once. `enrollments.preview_import` checks
the file without inviting anyone; `enrollments.import_` (with PEP 8's
trailing underscore, since `import` is a keyword) invites everyone in it
and returns an Operation. Both take the file as
a path (`str` or `pathlib.Path`), `bytes`, or a file opened with `"rb"`. A
`str` is always a path; pass CSV text as `text.encode()`. The file is read
once per call, so a retry resends the same bytes.

<!-- sample: csv-import -->
```python
from pathlib import Path

preview = client.enrollments.preview_import(
    file=Path("roster.csv"), options={"course_id": "hipaa-2026"}
)
print(preview.valid_rows, "of", preview.total_rows, "rows are valid")
client.enrollments.import_(file="roster.csv").wait()
```

## Downloading Certificate PDFs

`certificates.download_pdf` returns the whole file as a `BinaryResponse`
(`content`, `content_type`, `filename`). Pass `stream=True` to read one as
it arrives, the way `httpx` streams; close the stream, ideally with `with`.

<!-- sample: pdf-download -->
```python
from pathlib import Path

pdf = client.certificates.download_pdf("cert_01JD8F")
Path(pdf.filename or "certificate.pdf").write_bytes(pdf.content)

with (
    client.certificates.download_pdf("cert_01JD8F", stream=True) as stream,
    open("certificate-copy.pdf", "wb") as out,
):
    for chunk in stream.iter_bytes():
        out.write(chunk)
```

On the async client, `async with await client.certificates.download_pdf(...,
stream=True) as stream:` and `async for chunk in stream.aiter_bytes():`.
Revoked and expired Certificates download watermarked.
