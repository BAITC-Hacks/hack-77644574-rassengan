import json
import re
from copy import deepcopy
from itertools import combinations
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app import explain, llm
from app.data import DEFAULT_PATH, load_profiles
from app.explain_check import sentence_count, validate
from app.matching import match

QUERY = dict(city="Алматы", category="Ведущий", date="2026-10-15",
             event_type="свадьба", budget_kzt=1000000)


@pytest.fixture
def profiles():
    return load_profiles(DEFAULT_PATH)


def batch_stub(monkeypatch, transform=lambda text, i: text):
    def response(request, cards, timeout):
        return {c["id"]: transform("В описании профиля " + next(
            f["text"] for f in c["matched_facts"] if f["kind"] == "description") + ".", i)
                for i, c in enumerate(cards)}
    stub = MagicMock(side_effect=response)
    monkeypatch.setattr(explain, "explain_cards", stub)
    return stub


def test_no_key_templates(profiles):
    result = match(QUERY, profiles)
    assert result["explainer"] == "template"
    assert len(result["cards"]) == 3
    assert all(c["explanation_source"] == "template" and c["fallback_reason"] for c in result["cards"])
    assert llm.explain_cards(QUERY, result["cards"], 8) is None


def test_good_llm_output(profiles, monkeypatch):
    stub = batch_stub(monkeypatch)
    result = match(QUERY, profiles)
    assert result["explainer"] == "llm"
    assert all(c["explanation_source"] == "llm" and "fallback_reason" not in c for c in result["cards"])
    stub.assert_called_once()


@pytest.mark.parametrize("bad, reason", [
    ("Отличный выбор, цена 1000000 тенге.", "рекламная"),
    ("Для вашего мероприятия, цена 1000000 тенге.", "рекламная"),
    ("Прекрасный вариант, цена 1000000 тенге.", "рекламная"),
    ("Высокий профессионализм, цена 1000000 тенге.", "рекламная"),
    ("Идеально подойдёт, цена 1000000 тенге.", "рекламная"),
    ("Стоимость 987654321 тенге.", "Число"),
])
def test_rejected_output(profiles, monkeypatch, bad, reason):
    batch_stub(monkeypatch, lambda text, i: bad if i == 0 else text)
    result = match(QUERY, profiles)
    assert result["explainer"] == "mixed"
    card = result["cards"][0]
    assert card["explanation_source"] == "template"
    assert reason in card["fallback_reason"]


@pytest.mark.parametrize("identifier", ["HK-90001", "HK-12345", "hk-90001"])
def test_validator_rejects_internal_ids(identifier):
    card = {"matched_facts": [{"kind": "price", "text": "цена от 90001 тенге"}]}
    assert validate(f"У {identifier} цена от 90001 тенге.", card, []) == (
        False, "Упомянут внутренний идентификатор")


def test_mocked_llm_internal_id_falls_back(profiles, monkeypatch):
    cards = match(QUERY, profiles)["cards"]
    explain._CACHE.clear()
    _, client = mock_client(monkeypatch, {"explanations": [
        {"id": c["id"], "text": "У HK-90001 в описании есть опыт ведения свадеб."}
        for c in cards]})
    result = match(QUERY, profiles)
    client.chat.completions.create.assert_called_once()
    assert result["explainer"] == "template"
    for card in result["cards"]:
        assert card["explanation_source"] == "template"
        assert card["fallback_reason"] == "Упомянут внутренний идентификатор"
        assert card["explanation"] == explain.template_explanation(card, result["cards"])
        assert "HK-90001" not in card["explanation"]


def test_identical_text_second_falls_back(profiles, monkeypatch):
    batch_stub(monkeypatch, lambda text, i: "Принимает формат «свадьба».")
    cards = match(QUERY, profiles)["cards"]
    assert cards[0]["explanation_source"] == "llm"
    assert cards[1]["explanation_source"] == "template"
    assert "похоже" in cards[1]["fallback_reason"]


@pytest.mark.parametrize("error", [TimeoutError, RuntimeError])
def test_exception_fallback(profiles, monkeypatch, error):
    monkeypatch.setattr(explain, "explain_cards", MagicMock(side_effect=error))
    assert match(QUERY, profiles)["explainer"] == "template"


def test_dense_templates_distinct_and_short(profiles):
    cards = match(QUERY, profiles)["cards"]
    texts = [c["explanation"].replace(c["name"], "") for c in cards]
    assert len(cards) == 3
    assert all(a != b for a, b in combinations(texts, 2))
    assert all(sentence_count(t) <= 2 for t in texts)
    assert all("; " not in t for t in texts)


def test_cached_text_and_order(profiles, monkeypatch):
    baseline = match(QUERY, profiles)
    explain._CACHE.clear()
    stub = batch_stub(monkeypatch)
    first = match(QUERY, profiles)
    second = match(QUERY, list(reversed(profiles)))
    assert first == second
    assert [c["id"] for c in first["cards"]] == [c["id"] for c in baseline["cards"]]
    stub.assert_called_once()
    match(dict(QUERY, budget_kzt=1100000), profiles)
    assert stub.call_count == 2


def mock_client(monkeypatch, payload):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-placeholder")
    monkeypatch.setenv("OPENAI_MODEL", "organizer-model-placeholder")
    client = MagicMock()
    client.__enter__.return_value = client
    client.chat.completions.create.return_value = SimpleNamespace(choices=[
        SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))])
    constructor = MagicMock(return_value=client)
    monkeypatch.setattr(llm, "OpenAI", constructor)
    return constructor, client


def test_batch_api_contract(monkeypatch):
    constructor, client = mock_client(monkeypatch, {"explanations": [{"id": "A", "text": "Текст"}]})
    cards = [{"id": "A", "matched_facts": []}]
    assert llm.explain_cards(QUERY, cards, 1.5) == {"A": "Текст"}
    assert constructor.call_args.kwargs["timeout"] == 1.5
    assert constructor.call_args.kwargs["max_retries"] == 0
    params = client.chat.completions.create.call_args.kwargs
    assert params["temperature"] == 0
    assert params["response_format"] == {"type": "json_object"}
    assert json.loads(params["messages"][1]["content"])["cards"][0]["id"] == "A"
    assert json.loads(params["messages"][1]["content"])["shared_facts"] == []
    client.chat.completions.create.assert_called_once()


@pytest.mark.parametrize("same_price", [True, False])
def test_payload_shared_facts_are_common_to_every_card(monkeypatch, same_price):
    availability = {"kind": "availability", "text": "по календарю свободен на 2026-10-15"}
    event_format = {"kind": "format", "text": "принимает формат «свадьба»"}
    price = {"kind": "price", "text": "цена от 900 000 ₸ при бюджете 1 000 000 ₸"}
    cards = [{"id": ident, "matched_facts": [availability, event_format, price,
              {"kind": "description", "text": detail}]}
             for ident, detail in (("A", "Проводы невесты"), ("B", "Опыт 13 лет"), ("C", "Опыт 12 лет"))]
    if not same_price:
        cards[2]["matched_facts"][2] = dict(price, text="цена от 1 000 000 ₸ при бюджете 1 000 000 ₸")
    _, client = mock_client(monkeypatch, {"explanations": [
        {"id": c["id"], "text": "Текст"} for c in cards]})
    assert llm.explain_cards(QUERY, cards, 1.5) is not None
    payload = json.loads(client.chat.completions.create.call_args.kwargs["messages"][1]["content"])
    assert payload["shared_facts"] == [availability, event_format] + ([price] if same_price else [])
    assert payload["request"] == QUERY
    assert payload["cards"] == [{"id": c["id"], "facts": c["matched_facts"]} for c in cards]


@pytest.mark.parametrize("payload", [None, [], {}, {"explanations": "bad"},
    {"explanations": [{"id": "B", "text": "Текст"}]},
    {"explanations": [{"id": "A", "text": 123}]},
    {"explanations": [{"id": "A", "text": "a"}, {"id": "A", "text": "b"}]}])
def test_schema_fallback(monkeypatch, payload):
    mock_client(monkeypatch, payload)
    assert llm.explain_cards(QUERY, [{"id": "A", "matched_facts": []}], 8) is None


def test_api_timeout_and_safe_log(monkeypatch, caplog):
    _, client = mock_client(monkeypatch, {})
    client.chat.completions.create.side_effect = TimeoutError("offline-test-placeholder")
    assert llm.explain_cards(QUERY, [{"id": "A", "matched_facts": []}], 0.1) is None
    assert "TimeoutError" in caplog.text
    assert "offline-test-placeholder" not in caplog.text


@pytest.mark.parametrize("missing", ["OPENAI_API_KEY", "OPENAI_MODEL"])
def test_missing_config_no_client(monkeypatch, missing):
    constructor, _ = mock_client(monkeypatch, {})
    monkeypatch.delenv(missing)
    assert llm.explain_cards({}, [{"id": "A"}], 8) is None
    constructor.assert_not_called()


@pytest.mark.parametrize("text, ok", [
    ("", False), ("а" * 401, False),
    ("Свадьба. Свадьба. Свадьба.", False),
    ("Идеально подойдёт, цена 100000 тенге.", False),
    ("Для вашего мероприятия.", False),
    ("Цена от 100 000 тенге при бюджете 1\u00a0000\u00a0000 тенге.", True),
    ("Цена от 100001 тенге.", False),
    ("Принимает формат «свадьба».", True),
    ("Есть акустическая программа.", True),
    ("Работает 2,5 часа, формат «свадьба».", True),
])
def test_validator(text, ok):
    card = {"matched_facts": [
        {"kind": "price", "text": "цена от 100 000 ₸ при бюджете 1 000 000 ₸"},
        {"kind": "format", "text": "принимает формат «свадьба»"},
        {"kind": "hours", "text": "до 2.5 ч"},
        {"kind": "description", "text": "из описания: «Акустическая программа»"},
    ]}
    assert validate(text, card, [])[0] is ok


@pytest.mark.parametrize("day, ok", [
    ("2026-10-15", True), ("15.10.2026", True), ("15.10", True),
    ("16.10.2026", False), ("15.10.2027", False),
])
def test_validator_request_date_formats(day, ok):
    card = {"request": QUERY, "matched_facts": [
        {"kind": "availability", "text": "по календарю свободен на 2026-10-15"},
        {"kind": "format", "text": "принимает формат «свадьба»"},
    ]}
    assert validate(f"Свободен на {day}, принимает формат «свадьба».", card, [])[0] is ok
    assert not validate(f"Свободен на {day}, свадьба за 987654321 тенге.", card, [])[0]


@pytest.mark.parametrize("event, description, expected", [
    ("свадьба", "Ведёт все форматы: свадьбы, проводы невесты, обряд первых шагов, поминальный обед",
     "из описания: «Ведёт все форматы: свадьбы … проводы невесты»"),
    ("корпоратив", "Ведёт свадьбы, корпоративы и поминальные обеды",
     "из описания: «корпоративы»"),
    ("свадьба", "Опыт ведущего более 12 лет", "из описания: «Опыт ведущего более 12 лет»"),
    ("свадьба", "Поминальный обед", None),
    ("свадьба", "Не ведёт свадьбы, проводит корпоративы", "из описания: «Не ведёт свадьбы»"),
])
def test_llm_payload_trims_descriptions_without_mutating_cards(monkeypatch, event, description, expected):
    price = {"kind": "price", "text": "цена от 900 000 ₸ при бюджете 1 000 000 ₸"}
    cards = [{"id": ident, "matched_facts": [price,
              {"kind": "description", "text": "из описания: «" + description + "»"}]}
             for ident in ("A", "B")]
    original = deepcopy(cards)
    _, client = mock_client(monkeypatch, {"explanations": [
        {"id": c["id"], "text": "Текст"} for c in cards]})
    assert llm.explain_cards(dict(QUERY, event_type=event), cards, 1.5) is not None
    payload = json.loads(client.chat.completions.create.call_args.kwargs["messages"][1]["content"])
    expected_facts = [price] + ([{"kind": "description", "text": expected}] if expected else [])
    assert all(c["facts"] == expected_facts for c in payload["cards"])
    assert payload["shared_facts"] == expected_facts
    assert cards == original


def test_template_quotes_short_grounded_and_word_complete(profiles):
    cards = match(QUERY, profiles)["cards"]
    for card in cards:
        text = card["explanation"]
        description = explain._description(card)
        quotes = re.findall(r"«([^»]+)»", text)
        assert quotes
        for quote in quotes:
            assert len(quote) <= 90
            source = quote.rstrip("…")
            assert source in description
            end = description.index(source) + len(source)
            assert end == len(description) or not description[end].isalnum()
        assert next(f["text"] for f in card["matched_facts"] if f["kind"] == "price") in text
        assert "Обратите внимание" not in text
        assert validate(text, dict(card, request=QUERY), [])[0]
    assert "проводы невесты" in cards[0]["explanation"].split(". ")[0]
    assert "13 лет" in cards[1]["explanation"].split(". ")[0]
    assert "более 12 лет" in cards[2]["explanation"].split(". ")[0]


def test_template_price_comparison_uses_only_returned_cards(profiles):
    cards = match(QUERY, profiles)["cards"]
    # Tied minima and unknown peer prices must not produce a unique cheapest claim.
    assert all("Самая низкая" not in explain.template_explanation(c, cards) for c in cards)
    cards[0]["price_from_kzt"] = 800000
    assert explain.template_explanation(cards[0], cards).startswith("Самая низкая")
    assert "Самая низкая" not in explain.template_explanation(cards[0], [cards[0]])
    cards[1]["price_from_kzt"] = None
    assert "Самая низкая" not in explain.template_explanation(cards[0], cards)


def test_template_unique_format_mention(profiles):
    cards = match(QUERY, profiles)["cards"]
    cards[1]["score_breakdown"]["event_relevance"] = 0
    assert explain.template_explanation(cards[0], cards).startswith("Только в этом описании")
