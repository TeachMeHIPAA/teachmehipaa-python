# teachmehipaa

[![CI](https://github.com/TeachMeHIPAA/teachmehipaa-python/actions/workflows/ci.yml/badge.svg)](https://github.com/TeachMeHIPAA/teachmehipaa-python/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Official Python library for the TeachMeHIPAA Developer API.

## Documentation

**[docs.teachmehipaa.com/api](https://docs.teachmehipaa.com/api?lang=python)**
has the API reference with Python samples for every operation, plus guides
for authentication, pagination, errors and webhooks.

## Install

> [!NOTE]
> **Pre-release.** The Developer API isn't generally available yet and
> `teachmehipaa` isn't on PyPI. Install it from GitHub for now, and expect
> names and behavior to change before 1.0.0.

```sh
pip install "teachmehipaa @ git+https://github.com/TeachMeHIPAA/teachmehipaa-python"
```

Once it reaches PyPI, `pip install teachmehipaa` will do.

## Requirements

Python 3.10 or newer. Sync and async clients (`TeachMeHipaa`,
`AsyncTeachMeHipaa`) are built on `httpx` and pydantic.

## Usage

<!-- sample: quickstart -->
```python
import os

from teachmehipaa import TeachMeHipaa

client = TeachMeHipaa(
    client_id=os.environ["TMH_CLIENT_ID"],
    client_secret=os.environ["TMH_CLIENT_SECRET"],
    environment="sandbox",
)

for learner in client.learners.list(status="in_progress", limit=20):
    print(learner.email)
```

Get a client id (`cli_…`) and secret (`tmh_cs_…`) by creating an API client
in the TeachMeHIPAA console, in the Sandbox Environment
(`https://sandbox.api.tme.so/v1`) while you build. [`examples/`](examples/)
holds more programs to run against it.

## Support

<!-- TODO(Nick): confirm the support address before launch. -->

For help, contact TeachMeHIPAA support and include the `request_id` from the
exception or from `last_response`. Changes are in the
[changelog](CHANGELOG.md).

## Security

Report vulnerabilities privately, as [SECURITY.md](SECURITY.md) describes.

## Contributing

To hack on the library itself, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT, see [LICENSE](LICENSE).
