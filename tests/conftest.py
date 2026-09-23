"""All tests are offline, including when .env contains real credentials."""
import pytest

from app import explain, llm


@pytest.fixture(autouse=True)
def offline_explainer(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_MODEL", "")
    def forbidden_client(**kwargs):
        raise AssertionError("Real API clients are forbidden in tests")
    monkeypatch.setattr(llm, "OpenAI", forbidden_client)
    explain._CACHE.clear()
    yield
    explain._CACHE.clear()
