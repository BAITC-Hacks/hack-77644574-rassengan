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


def test_options_from_loaded_dataset(client):
    from app.matching import dataset_options
    response = client.get("/options")
    assert response.status_code == 200
    assert response.json() == dataset_options(app.state.profiles)
    assert set(response.json()) == {"cities", "categories", "event_formats", "languages"}
    assert all(values == sorted(set(values)) for values in response.json().values())
    page = client.get("/").text
    assert "fetch('/options')" in page
    assert '<select name="category"' in page
    assert "score_breakdown" in page and "data.trace" in page
