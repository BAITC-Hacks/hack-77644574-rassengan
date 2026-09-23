"""DoD2 regression: explanations of one response must differ with names removed (template mode).

Found by the team's acceptance review: two live bands whose descriptions start identically got the
same template text. Differences must come from the catalogue text, never from names or ids.
"""
import pytest

from app.data import load_profiles
from app.explain_check import normalized, sentence_count
from app.matching import match


@pytest.fixture(scope="module")
def profiles():
    return load_profiles("data/hackathon-dataset-anonymized.csv")


@pytest.fixture(autouse=True)
def template_mode(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_MODEL", "")


def _keys(cards):
    return [normalized(c["explanation"].replace(c["name"], "")) for c in cards]


def test_live_bands_with_identical_opening_are_distinct(profiles):
    result = match(dict(city="Алматы", date="2026-10-15", event_type="корпоратив",
                        category="Лайв-бэнд", budget_kzt=4000000), profiles)
    cards = result["cards"]
    assert len(cards) >= 2
    assert len(set(_keys(cards))) == len(cards)
    for card in cards:
        assert card["id"] not in card["explanation"]


def test_no_duplicate_explanations_across_catalogue_grid(profiles):
    combos = sorted({(p.city, c, f) for p in profiles for c in p.categories for f in p.event_formats})
    duplicates, checked = [], 0
    for city, category, event_type in combos:
        for day in ("2026-09-23", "2026-10-15", "2026-11-14", "2026-12-31"):
            for budget in (500000, 1000000, 4000000):
                cards = match(dict(city=city, date=day, event_type=event_type, category=category,
                                   budget_kzt=budget), profiles)["cards"]
                if not cards:
                    continue
                checked += 1
                assert all(sentence_count(c["explanation"]) <= 2 for c in cards)
                if len(set(_keys(cards))) < len(cards):
                    duplicates.append((city, category, event_type, day, budget))
    assert checked > 600
    assert duplicates == []
