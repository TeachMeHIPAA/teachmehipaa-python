# Examples

Small programs that use the library against the Sandbox. Each reads an API
client's credentials from `TMH_CLIENT_ID` and `TMH_CLIENT_SECRET` (create
one in the Sandbox Environment; see
[the docs](https://docs.teachmehipaa.com/api?lang=python)). CI type-checks them
with mypy but doesn't run them.

| Example                                            | What it does                                                    |
| -------------------------------------------------- | --------------------------------------------------------------- |
| [`quickstart.py`](quickstart.py)                   | Prints the Compliance summary and the first page of Learners    |
| [`sync_roster.py`](sync_roster.py)                 | Syncs a roster CSV with upserts by External ID                  |
| [`webhook_server.py`](webhook_server.py)           | A Flask endpoint that verifies Deliveries and handles Events    |
| [`export_certificates.py`](export_certificates.py) | Exports Certificates to a CSV file and waits for the Operation |

From a checkout of this repository:

```sh
uv sync
export TMH_CLIENT_ID=cli_... TMH_CLIENT_SECRET=tmh_cs_...
uv run python examples/quickstart.py
uv run python examples/sync_roster.py roster.csv hipaa-2026
uv run python examples/export_certificates.py certificates.csv
TMH_WEBHOOK_SECRET=... uv run flask --app examples/webhook_server run --port 8000
```

`webhook_server.py` needs a webhook Signing secret in `TMH_WEBHOOK_SECRET`
instead of API credentials: the one returned when you created the Webhook
subscription.
