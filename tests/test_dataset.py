import json
from dataclasses import asdict
from pathlib import Path

from app.data import load_profiles
from app.matching import match

ROOT = Path(__file__).resolve().parent.parent


def test_official_dataset():
    profiles = load_profiles(ROOT / "data/hackathon-dataset-anonymized.csv")
    assert len(profiles) == 66
    result = match(dict(city="Алматы", category="Ведущий", date="2026-10-15", event_type="свадьба", budget_kzt=1000000), profiles)
    assert result["outcome"] == "found"


def test_jsonl_and_env_path(tmp_path, monkeypatch):
    profiles = load_profiles(ROOT / "tests/fixtures/profiles_sample.csv")
    assert len(profiles) == 10
    assert all(p.synthetic for p in profiles)
    path = tmp_path / "profiles.jsonl"
    path.write_text("\n".join(json.dumps(asdict(p), ensure_ascii=False) for p in profiles), encoding="utf-8")
    monkeypatch.setenv("DATA_PATH", str(path))
    assert load_profiles() == profiles
