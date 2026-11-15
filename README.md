# teachmehipaa

The official Python library for the TeachMeHIPAA Developer API.

> Pre-release. Nothing is published to PyPI yet.

```python
from teachmehipaa import TeachMeHipaa

with TeachMeHipaa(
    client_id="cli_...",
    client_secret="tmh_cs_...",
    environment="sandbox",
) as client:
    learner = client.learners.retrieve("sub_...")
    print(learner.status, learner.last_response.request_id)
```

`AsyncTeachMeHipaa` has the same surface with `await`.
