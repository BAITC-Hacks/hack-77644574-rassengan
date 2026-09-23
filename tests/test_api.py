from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DATA_PATH", str(Path(__file__).parent / "fixtures/profiles_sample.csv"))
    with TestClient(app) as session:
        yield session


def test_end_to_end(client):
    assert client.get("/health").json() == {"status": "ok", "profiles": 10}
    assert "Подбор подрядчиков" in client.get("/").text
    response = client.post("/match", json=dict(city="Астана", category="Ведущий", date="2026-10-15", event_type="свадьба", budget_kzt=300000))
    assert response.status_code == 200
    assert response.json()["outcome"] == "found"
    assert all(c["synthetic"] for c in response.json()["cards"])


@pytest.mark.parametrize("changes", [{"date": "2026-02-30"}, {"budget_kzt": -1}, {"hours": 0}, {"city": " "}])
def test_invalid_input(client, changes):
    request = dict(city="Астана", category="Ведущий", date="2026-10-15", event_type="свадьба", budget_kzt=300000)
    request.update(changes)
    assert client.post("/match", json=request).status_code == 422
