"""Acceptance checks use the official CSV, never the sample fixture or DATA_PATH."""
import re
from datetime import date
from time import perf_counter

import pytest

from app.data import DEFAULT_PATH, load_profiles
from app.matching import match
from app.explain_check import sentence_count, validate


@pytest.fixture(scope="module")
def profiles():
    return load_profiles(DEFAULT_PATH)


@pytest.fixture(scope="module")
def dense_case(profiles):
    dates = sorted({d for p in profiles for d in p.busy_dates if date.fromisoformat(d).month in (9, 10, 11)})
    formats = sorted({f for p in profiles for f in p.event_formats})
    budget = max(p.price_from_kzt or 0 for p in profiles)
    for day in dates:
        for event in formats:
            query = dict(city="Алматы", category="Ведущий", event_type=event, date=day, budget_kzt=budget)
            if len(match(query, profiles)["cards"]) == 3:
                return query
    pytest.fail("No dense autumn scenario found in official data")


def test_dod1_matching_under_one_second(profiles, dense_case):
    start = perf_counter()
    result = match(dense_case, profiles)
    assert perf_counter() - start < 1
    assert result["cards"]


def test_dod2_explanations_grounded_and_distinct(profiles, dense_case):
    cards = match(dense_case, profiles)["cards"]
    explanations = [c["explanation"].replace(c["name"], "") for c in cards]
    assert len(set(explanations)) == len(cards)
    for card in cards:
        # The explanation selects distinguishing facts rather than reciting them all.
        assert validate(card["explanation"], dict(card, request=dense_case), [])[0]
        assert sentence_count(card["explanation"]) <= 2
        price = next(f["text"] for f in card["matched_facts"] if f["kind"] == "price")
        assert price in card["explanation"]
        description = next(f["text"] for f in card["matched_facts"] if f["kind"] == "description")
        quote = re.findall(r"«([^»]+)»", card["explanation"])[-1]
        assert len(quote) <= 90 and quote.rstrip("…") in description
        assert any(f["kind"] == "description" for f in card["matched_facts"])


def test_dod3_same_request_three_times(profiles, dense_case):
    orders = [[c["id"] for c in match(dense_case, profiles)["cards"]] for _ in range(3)]
    assert orders[0] == orders[1] == orders[2]


def test_dod4_calendar_changes_results_and_explains_busy(profiles, dense_case):
    first = match(dense_case, profiles)
    first_ids = [c["id"] for c in first["cards"]]
    # Search actual calendars of returned profiles for the second date.
    dates = sorted({d for p in profiles if p.id in first_ids for d in p.busy_dates})
    for day in dates:
        second = match(dict(dense_case, date=day), profiles)
        busy = [t for t in second["trace"] if t["id"] in first_ids and t["reason"]
                and "занят" in t["reason"]]
        if busy:
            assert first_ids != [c["id"] for c in second["cards"]]
            assert all(date.fromisoformat(day).strftime("%d.%m.%Y") in t["reason"] for t in busy)
            return
    pytest.fail("No calendar-driven change found")


def test_dod5_dense_rare_and_empty(profiles, dense_case):
    assert len(match(dense_case, profiles)["cards"]) == 3
    rare = match(dict(dense_case, category="Флорист"), profiles)
    assert 0 < rare["candidate_count"] <= 3
    assert len(rare["cards"]) <= 3
    if len(rare["cards"]) < 3:
        assert rare["why_fewer_than_3"]
    empty = match(dict(dense_case, event_type="несуществующий формат"), profiles)
    assert empty["outcome"] in ("no_match", "no_category_in_city")
    assert empty["message"]


def test_dod6_empty_results_have_russian_messages(profiles, dense_case):
    for changes in (dict(city="Несуществующий город"), dict(category="Несуществующая категория"),
                    dict(event_type="несуществующий формат"), dict(hours=100000, language="несуществующий язык")):
        result = match(dict(dense_case, **changes), profiles)
        assert not result["cards"]
        assert re.search("[А-Яа-я]", result["message"])


def test_dod7_trace_and_score_are_auditable(profiles, dense_case):
    result = match(dense_case, profiles)
    assert len(result["trace"]) == result["candidate_count"]
    rejected = [t for t in result["trace"] if t["status"] == "rejected"]
    assert len(rejected) == sum(result["rejection_counts"].values())
    assert all(t["reason"] and t["score"] is None for t in rejected)
    assert sum(t["status"] == "passed" for t in result["trace"]) == result["passing_count"]
    for card in result["cards"]:
        assert card["score"] == round(sum(card["score_breakdown"].values()), 8)
        assert next(t["score"] for t in result["trace"] if t["id"] == card["id"]) == card["score"]
