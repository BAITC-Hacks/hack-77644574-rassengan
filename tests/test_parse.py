"""Free-text parsing contract and API checks; never contacts an LLM."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import llm
from app.main import app

OPTIONS = dict(cities=['Алматы'], categories=['Ведущий'], event_formats=['той'], languages=['казахский'])
GOOD = dict(city='Алматы', date='2026-11-14', event_type='той', category='Ведущий',
            budget_kzt=500000, hours=None, language='казахский', missing=[])
TEXT = 'Нужен ведущий на казахском на той 14 ноября в Алматы, бюджет до 500 тысяч'
ERROR = ('Не удалось разобрать текст: AI не ответил вовремя или вернул некорректный ответ; '
         'заполните форму вручную')
NO_KEY_ERROR = ('Разбор текста доступен только с ключом OpenAI и моделью (OPENAI_API_KEY, OPENAI_MODEL); '
                'заполните форму')
CALENDAR_MESSAGE = 'Календарь занятости покрывает только 23.09.2026–31.12.2026; выберите дату в этом диапазоне.'


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('DATA_PATH', str(Path(__file__).parent / 'fixtures/profiles_sample.csv'))
    with TestClient(app) as session:
        yield session


def mock_llm(monkeypatch, payload):
    monkeypatch.setenv('OPENAI_API_KEY', 'offline-test-placeholder')
    monkeypatch.setenv('OPENAI_MODEL', 'test-model')
    client = MagicMock()
    client.__enter__.return_value = client
    client.chat.completions.create.return_value = SimpleNamespace(choices=[
        SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))])
    constructor = MagicMock(return_value=client)
    monkeypatch.setattr(llm, 'OpenAI', constructor)
    return constructor, client


def test_parse_one_call_and_validated_fields(monkeypatch):
    constructor, client = mock_llm(monkeypatch, GOOD)
    assert llm.parse_request(TEXT, OPTIONS, 3) == GOOD
    constructor.assert_called_once_with(api_key='offline-test-placeholder', timeout=3, max_retries=0)
    client.chat.completions.create.assert_called_once()
    args = client.chat.completions.create.call_args.kwargs
    assert args['temperature'] == 0
    assert args['response_format'] == {'type': 'json_object'}
    assert json.loads(args['messages'][1]['content']) == {'text': TEXT, 'options': OPTIONS}


def test_parse_api_fills_fields(client, monkeypatch):
    mock_llm(monkeypatch, GOOD)
    response = client.post('/parse', json={'text': TEXT})
    assert response.status_code == 200
    assert response.json() == dict(fields={k: v for k, v in GOOD.items() if k != 'missing'},
                                   missing=[], source='llm')


@pytest.mark.parametrize('field', ['city', 'category', 'event_type', 'language'])
def test_unlisted_options_are_not_trusted(client, monkeypatch, field):
    mock_llm(monkeypatch, dict(GOOD, **{field: 'invented'}))
    data = client.post('/parse', json={'text': TEXT}).json()
    assert data['fields'][field] is None
    assert field in data['missing']


@pytest.mark.parametrize('day', ['2026-09-22', '2027-01-01', '2026-01-01'])
def test_outside_calendar(client, monkeypatch, day):
    mock_llm(monkeypatch, dict(GOOD, date=day))
    data = client.post('/parse', json={'text': TEXT}).json()
    assert data['fields']['date'] is None
    assert data['missing'] == ['date', CALENDAR_MESSAGE]


@pytest.mark.parametrize('day', ['2026-09-23', '2026-12-31'])
def test_calendar_boundaries(monkeypatch, day):
    mock_llm(monkeypatch, dict(GOOD, date=day))
    assert llm.parse_request(TEXT, OPTIONS, 3)['date'] == day


@pytest.mark.parametrize('day', ['2026-11-31', '14.11.2026', '20261114'])
def test_invalid_date_requires_clarification(monkeypatch, day):
    mock_llm(monkeypatch, dict(GOOD, date=day))
    result = llm.parse_request(TEXT, OPTIONS, 3)
    assert result['date'] is None and result['missing'] == ['date']


def test_missing_required_fields_recomputed(monkeypatch):
    mock_llm(monkeypatch, dict(GOOD, date=None, budget_kzt=None, language=None))
    result = llm.parse_request('Нужен ведущий', OPTIONS, 3)
    assert result['missing'] == ['date', 'budget_kzt']
    assert result['date'] is None and result['budget_kzt'] is None


def test_model_marks_value_unknown(monkeypatch):
    mock_llm(monkeypatch, dict(GOOD, missing=['budget_kzt']))
    result = llm.parse_request(TEXT, OPTIONS, 3)
    assert result['budget_kzt'] is None
    assert result['missing'] == ['budget_kzt']


@pytest.mark.parametrize('payload', [
    None, [], {}, dict(GOOD, extra='injected'), {k: v for k, v in GOOD.items() if k != 'hours'},
    dict(GOOD, budget_kzt='500к'), dict(GOOD, budget_kzt=True), dict(GOOD, budget_kzt=500.5),
    dict(GOOD, budget_kzt=-1), dict(GOOD, hours=True), dict(GOOD, hours=0),
    dict(GOOD, hours=float('nan')), dict(GOOD, city=['Алматы']), dict(GOOD, missing='date'),
    dict(GOOD, missing=['injected']), dict(GOOD, missing=[{}]),
])
def test_malformed_llm_output_rejected(client, monkeypatch, payload):
    mock_llm(monkeypatch, payload)
    response = client.post('/parse', json={'text': TEXT})
    assert response.status_code == 200
    assert response.json() == dict(fields=None, missing=[], error=ERROR)


@pytest.mark.parametrize('missing', ['OPENAI_API_KEY', 'OPENAI_MODEL'])
def test_missing_configuration(client, monkeypatch, missing):
    constructor, _ = mock_llm(monkeypatch, GOOD)
    monkeypatch.delenv(missing)
    assert client.post('/parse', json={'text': TEXT}).json() == dict(fields=None, missing=[], error=NO_KEY_ERROR)
    constructor.assert_not_called()


@pytest.mark.parametrize('error', [TimeoutError, RuntimeError])
def test_llm_failure(client, monkeypatch, error):
    _, fake = mock_llm(monkeypatch, GOOD)
    fake.chat.completions.create.side_effect = error('offline-test-placeholder')
    assert client.post('/parse', json={'text': TEXT}).json() == dict(fields=None, missing=[], error=ERROR)
    fake.chat.completions.create.assert_called_once()


@pytest.mark.parametrize('text', ['', '   ', 'а' * 501, None, 123])
def test_invalid_input(client, text):
    assert client.post('/parse', json={'text': text}).status_code == 422
