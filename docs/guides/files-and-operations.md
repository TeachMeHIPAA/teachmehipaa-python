# Exports, imports and PDFs

Exports, CSV imports, batch writes, Test deliveries and redrives can outlast
the request that starts them, so their methods return an Operation for you
to wait on. Certificate PDFs come back as bytes or as a stream. Samples use
a `client` built as in the [Quickstart](quickstart.md#make-a-request).

## Wait for an Operation

An `Operation` (`AsyncOperation` on the async client) has a `name`, a
`done` flag and, once done, either a `response` or an `error`. Call
`wait()` to poll until it's done:

<!-- sample: operations -->
```python
operation = client.learners.export(format="csv", course_id="hipaa-2026")
done = operation.wait(timeout=60, interval=2)
export = done.export_result()
print(export.filename, export.row_count, len(export.csv))
```

`wait()` first waits `interval` seconds (1 by default), then doubles the
wait between polls, with jitter, up to 10 s, and returns the finished
Operation. It raises
`OperationTimeoutError` once `timeout` seconds pass (300 by default) and
`OperationFailedError` when the Operation ends in an error. Both exceptions
carry the `operation`. An Operation that came back already done, as exports
do, returns from `wait()` without another request.

To check on an Operation from somewhere else, a second process or a later
cron run, store its `name`. `operation_id_from_name(operation.name)` turns
it into the id that `client.operations.retrieve()` takes.

## Export to a CSV file

`certificates.export`, `enrollments.export` and `learners.export` each build
one RFC 4180 CSV file with CRLF line endings, and `export_result()` hands it
to you as `export.csv`. Write it with `newline=""` so Python leaves those
line endings alone:

<!-- sample: certificates-export -->
```python
from pathlib import Path

export = client.certificates.export(format="csv").wait().export_result()
Path(export.filename or "certificates.csv").write_text(export.csv, newline="")
print(export.row_count, "Certificates exported")
```

When an export would be too large for one file, the call raises
`InvalidRequestError` with `code == "export_too_large"`. `learners.export`
covers one Course; pass `status` to narrow it further.

## Import Enrollments from a CSV file

Give the API a CSV file with an `email` column, plus optional `name` and
`courseId` columns, and it enrolls up to 500 people in one go.
`enrollments.preview_import()` validates the file without inviting anyone.
`enrollments.import_()` does the inviting and returns an Operation. (PEP 8's
trailing underscore keeps it clear of the `import` keyword.)

<!-- sample: csv-import -->
```python
from pathlib import Path

preview = client.enrollments.preview_import(
    file=Path("roster.csv"), options={"course_id": "hipaa-2026"}
)
print(preview.valid_rows, "of", preview.total_rows, "rows are valid")
client.enrollments.import_(file="roster.csv").wait()
```

`file` takes a path (`str` or `pathlib.Path`), `bytes`, or a file object
opened in `"rb"` mode. A `str` always means a path, so pass CSV you built in
memory as `text.encode()`. The client reads the file once per call, which
means a retry resends identical bytes.

## Download a Certificate PDF

`certificates.download_pdf()` returns a `BinaryResponse` with `content`,
`content_type` and `filename`. For big files, pass `stream=True` and read
chunks the way you would from an `httpx` streaming response. Close the
stream when you're done; a `with` block does it for you.

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

The parenthesized `with` needs Python 3.10, which is also this library's
minimum. On the async client, write `async with await
client.certificates.download_pdf(..., stream=True) as stream:` and
`async for chunk in stream.aiter_bytes():`. Revoked and expired Certificates
download with a watermark.
