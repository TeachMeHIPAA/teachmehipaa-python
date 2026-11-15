import pytest

from tests.fake_api import FakeApi, FakeClock, script_learner_retrieve


@pytest.fixture
def api() -> FakeApi:
    fake = FakeApi()
    script_learner_retrieve(fake)
    return fake


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()
