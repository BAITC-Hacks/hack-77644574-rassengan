from dataclasses import replace
from pathlib import Path

import pytest

from app.data import load_profiles
from app.matching import match

FIXTURE = Path(__file__).parent / "fixtures/profiles_sample.csv"


@pytest.fixture
def profiles():
    return load_profiles(FIXTURE)


@pytest.fixture
def request_data():
    return dict(city="Астана", date="2026-10-15", event_type="свадьба", category="Ведущий", budget_kzt=300000)


def test_busy_excluded(profiles, request_data):
    result = match(request_data, profiles)
    assert "S01" not in [c["id"] for c in result["cards"]]
    assert result["rejection_counts"]["busy"] == 1


def test_determinism(profiles, request_data):
    assert match(request_data, profiles) == match(request_data, list(reversed(profiles)))
    assert match(request_data, profiles) == match(request_data, profiles)


def test_two_dates(profiles, request_data):
    first = match(request_data, profiles)
    second = match(dict(request_data, date="2026-10-16"), profiles)
    assert [c["id"] for c in first["cards"]] != [c["id"] for c in second["cards"]]
    assert second["rejection_counts"]["busy"] == 3
    assert "заняты" in second["why_fewer_than_3"]


def test_no_category(profiles, request_data):
    result = match(dict(request_data, category="Флорист"), profiles)
    assert result["outcome"] == "no_category_in_city"
    assert not result["cards"]


def test_none_pass(profiles, request_data):
    result = match(dict(request_data, event_type="конференция"), profiles)
    assert result["outcome"] == "no_match"
    assert result["rejection_counts"] == dict(busy=1, event_format=3, budget=0, hours=0, language=0)


def test_fewer_than_three(profiles, request_data):
    result = match(dict(request_data, budget_kzt=160000), profiles)
    assert len(result["cards"]) == 2
    assert "цена выше бюджета: 1" in result["why_fewer_than_3"]


def test_different_explanations(profiles, request_data):
    cards = match(request_data, profiles)["cards"]
    assert len(set(c["explanation"] for c in cards)) == len(cards)
    assert all(c["matched_facts"] for c in cards)


def test_unknowns_do_not_reject(profiles, request_data):
    result = match(dict(request_data, budget_kzt=160000, hours=5), profiles)
    assert {c["id"] for c in result["cards"]} == {"S03", "S04"}
    unknown = next(c for c in result["cards"] if c["id"] == "S04")
    assert unknown["price_unknown"]
    assert "требует подтверждения" in unknown["explanation"]


@pytest.mark.parametrize("changes, reason", [
    ({"busy_dates": ["2026-10-15"], "event_formats": []}, "busy"),
    ({"event_formats": [], "price_from_kzt": 999999}, "event_format"),
    ({"price_from_kzt": 999999, "max_hours": 1}, "budget"),
    ({"max_hours": 1, "languages": []}, "hours"),
    ({"languages": []}, "language"),
])
def test_first_rejection_reason(profiles, request_data, changes, reason):
    p = replace(profiles[1], **changes)
    result = match(dict(request_data, hours=5, language="русский"), [p])
    assert result["rejection_counts"][reason] == 1
    assert sum(result["rejection_counts"].values()) == 1


def test_price_ranking_and_id_tie(profiles, request_data):
    base = profiles[1]
    choices = [replace(base, id="B"), replace(base, id="A"), replace(base, id="C", price_from_kzt=200000)]
    assert [c["id"] for c in match(request_data, choices)["cards"]] == ["A", "B", "C"]


def test_rare_category_without_rejections(profiles, request_data):
    result = match(dict(request_data, city="Алматы", category="Флорист"), profiles)
    assert result["outcome"] == "found"
    assert "всего 1 профилей" in result["why_fewer_than_3"]
