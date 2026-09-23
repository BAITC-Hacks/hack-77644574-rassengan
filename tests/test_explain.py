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
    assert payload["cards"] == [{"id": c["id"], "facts": c["matched_facts"],
                                  "price_unknown": True, "price_imputed": False} for c in cards]


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
    assert "свадьбы" in cards[0]["explanation"].split(". ")[0]
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


@pytest.mark.parametrize('filler', ['Деталей нет', 'Нет сведений', 'Не указано', 'Сравнение ограничивается ценой'])
def test_absence_filler_rejected(profiles, monkeypatch, filler):
    batch_stub(monkeypatch, lambda text, i: filler + ', цена 1000000 тенге.' if i == 0 else text)
    card = match(QUERY, profiles)['cards'][0]
    assert card['explanation_source'] == 'template'
    assert card['fallback_reason'] == 'Пустая фраза об отсутствии данных'


@pytest.mark.parametrize('language_text, ok', [('', False), ('Язык — казахский.', True), ('Ведёт на казахском.', True)])
def test_requested_language_required(language_text, ok):
    card = {'request': dict(QUERY, language='казахский'), 'matched_facts': [
        {'kind': 'language', 'text': 'язык работы — казахский'},
        {'kind': 'price', 'text': 'цена от 1000000 тенге'}]}
    result = validate('Цена от 1000000 тенге. ' + language_text, card, [])
    assert result[0] is ok
    if not ok:
        assert result[1] == 'Не подтверждён запрошенный язык'


def test_missing_language_llm_falls_back_and_template_confirms(profiles, monkeypatch):
    batch_stub(monkeypatch)
    cards = match(dict(QUERY, language='казахский', event_type='той'), profiles)['cards']
    assert cards
    assert all(c['explanation_source'] == 'template' for c in cards)
    assert all(c['fallback_reason'] == 'Не подтверждён запрошенный язык' for c in cards)
    assert all('казахский' in c['explanation'] for c in cards)
    assert 'той обрезания' in cards[0]['explanation']
    assert all(sentence_count(c['explanation']) <= 2 for c in cards)


@pytest.mark.parametrize('description', [
    'Приветствую всех, дорогие друзья! Веду той с живой музыкой.',
    'Профессиональный ведущий с интеллигентной ' + 'подачей ' * 25 + '. Веду той с живой музыкой.',
    'Организация мероприятий в ' + 'просторных залах ' * 20 + '. Веду той с живой музыкой.',
])
def test_template_uses_complete_rank_clause_not_greeting(profiles, description):
    from dataclasses import replace
    profile = replace(profiles[0], description=description, city='Алматы', categories=['Ведущий'],
                      event_formats=['той'], languages=['казахский'], busy_dates=[], price_from_kzt=100000)
    card = match(dict(QUERY, event_type='той', language='казахский'), [profile])['cards'][0]
    assert '«Веду той с живой музыкой»' in card['explanation']
    assert 'казахский' in card['explanation']
    assert 'Приветствую' not in card['explanation']
    assert 'дорогие друзья' not in card['explanation']
    assert 'интеллигентной»' not in card['explanation']
    assert 'в…' not in card['explanation']


def test_incomplete_quotes_are_omitted():
    assert explain._short_quote('Профессиональный ведущий с интеллигентной…') == ''
    assert explain._short_quote('Организация мероприятий в…') == ''
    assert explain._short_quote('Приветствую всех, дорогие друзья') == ''


def test_rank_facts_reach_llm_and_city_lists_are_removed(profiles, monkeypatch):
    query = dict(QUERY, event_type='той', language='казахский')
    cards = match(query, profiles)['cards']
    _, client = mock_client(monkeypatch, {'explanations': [{'id': c['id'], 'text': 'Текст'} for c in cards]})
    assert llm.explain_cards(query, cards, 1) is not None
    sent = json.loads(client.chat.completions.create.call_args.kwargs['messages'][1]['content'])
    assert any(f['kind'] == 'rank_reason' and 'той обрезания' in f['text'] for f in sent['cards'][0]['facts'])
    text = 'из описания: «Опыт ведения свадеб 13 лет, Москве, Дубае, Бодруме, Ташкенте»'
    trimmed = llm._description_for_event(text, 'свадьба', 'Алматы')
    assert trimmed == 'из описания: «Опыт ведения свадеб 13 лет»'


@pytest.mark.parametrize('term', ['rank_reason', 'score', 'facts', 'shared_facts', 'matched_facts', 'SCORE'])
def test_internal_terms_trigger_template(profiles, monkeypatch, term):
    batch_stub(monkeypatch, lambda text, i: f'В {term} совпадает формат «свадьба».' if i == 0 else text)
    card = match(QUERY, profiles)['cards'][0]
    assert card['explanation_source'] == 'template'
    assert card['fallback_reason'] == 'Технический термин в тексте'


@pytest.mark.parametrize('phrase', ['Часы не заданы', 'Язык не задан', 'Длительность не задана'])
def test_unrequested_field_filler_rejected(phrase):
    assert validate(phrase + ', формат «свадьба».', {}, []) == (
        False, 'Пустая фраза об отсутствии данных')


@pytest.mark.parametrize('phrase', ['Цену нужно подтвердить', 'Цена требует подтверждения'])
@pytest.mark.parametrize('price, imputed, allowed', [(100000, False, False), (100000, True, True), (None, False, True), (0, False, False)])
def test_price_confirmation_only_when_uncertain(phrase, price, imputed, allowed):
    card = {'price_from_kzt': price, 'price_unknown': price is None, 'price_imputed': imputed,
            'matched_facts': [{'kind': 'format', 'text': 'принимает формат «свадьба»'}]}
    result = validate(phrase + ', формат «свадьба».', card, [])
    assert result[0] is allowed
    if not allowed:
        assert result[1] == 'Известная цена не требует подтверждения'


def test_three_llm_sentences_trigger_template(profiles, monkeypatch):
    batch_stub(monkeypatch, lambda text, i: 'Принимает формат «свадьба». Цена от 1000000 тенге. Бюджет 1000000 тенге.' if i == 0 else text)
    card = match(QUERY, profiles)['cards'][0]
    assert card['fallback_reason'] == 'Больше двух предложений'
    assert card['explanation_source'] == 'template'
    assert sentence_count(card['explanation']) == 2


@pytest.mark.parametrize('intro', ['Меня зовут Альфонс Элрик', 'Я — Альфонс Элрик', 'Я - Альфонс', 'Привет', 'Приветствую'])
def test_template_skips_self_introductions(intro):
    card = {'id': 'test', 'name': 'Имя', 'price_from_kzt': 100000, 'matched_facts': [
        {'kind': 'description', 'text': f'из описания: «{intro}. Работаю с живой музыкой»'},
        {'kind': 'price', 'text': 'цена от 100000 тенге при бюджете 200000 тенге'},
        {'kind': 'format', 'text': 'принимает формат «той»'}]}
    text = explain.template_explanation(card)
    assert intro not in text
    assert 'Работаю с живой музыкой' in text
    assert sentence_count(text) == 2
    assert 'карточк' not in text
    assert 'час' not in text and 'язык' not in text
    assert 'подтвердить' not in text and 'подтверждения' not in text


def test_name_only_filter_preserves_service_description():
    assert explain._short_quote('Я — ведущий с опытом 12 лет') == 'Я — ведущий с опытом 12 лет'


@pytest.mark.parametrize('unknown, imputed', [(False, False), (False, True), (True, False)])
def test_llm_receives_price_certainty_and_prompt_rules(monkeypatch, unknown, imputed):
    _, client = mock_client(monkeypatch, {'explanations': [{'id': 'A', 'text': 'Текст'}]})
    card = {'id': 'A', 'matched_facts': [], 'price_unknown': unknown, 'price_imputed': imputed}
    assert llm.explain_cards(QUERY, [card], 1) is not None
    messages = client.chat.completions.create.call_args.kwargs['messages']
    sent = json.loads(messages[1]['content'])['cards'][0]
    assert sent['price_unknown'] is unknown and sent['price_imputed'] is imputed
    prompt = messages[0]['content']
    assert 'ровно 2 предложения, второе короткое' in prompt
    assert 'Не упоминай незапрошенные поля' in prompt
    assert 'ТОЛЬКО если price_unknown=true' in prompt
    assert 'Никогда не используй в тексте внутренние названия' in prompt
