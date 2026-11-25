import pytest

from tau2.domains.automation_workplace.families import access_provisioning


@pytest.fixture(autouse=True)
def offline_content_judge(monkeypatch):
    """Grade message content without calling a model during unit tests."""
    monkeypatch.setattr(access_provisioning, "CONTENT_JUDGE", lambda text, rubric: True)
    access_provisioning._JUDGE_CACHE.clear()
    yield
    access_provisioning._JUDGE_CACHE.clear()
