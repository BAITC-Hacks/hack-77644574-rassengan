"""Opt-in live evaluation. Run make eval with OPENAI_API_KEY and OPENAI_MODEL."""
from collections import Counter
from datetime import datetime
from itertools import combinations
import os
from pathlib import Path
import re
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from app import explain
from app.data import DEFAULT_PATH, load_profiles
from app.explain_check import normalized
from app.matching import match

# Fixed catalogue anchors: (profile id, category index, event index).
# Their actual catalogue fields supply city, category, format, price and options.
SEEDS = (
    ("HK-27222", 0, 0), ("HK-26808", 0, 1), ("HK-76335", 0, 1),
    ("HK-39372", 0, 0), ("HK-90002", 0, 0), ("HK-11484", 0, 0),
    ("HK-60927", 0, 3), ("HK-90006", 0, 1), ("HK-77793", 0, 1),
    ("HK-90008", 0, 0), ("HK-35846", 0, 0), ("HK-90010", 0, 2),
    ("HK-72785", 1, 1), ("HK-90012", 1, 0), ("HK-46450", 0, 2),
    ("HK-74147", 0, 0), ("HK-58236", 0, 0), ("HK-64395", 1, 0),
    ("HK-50695", 1, 2), ("HK-23752", 0, 0), ("HK-19103", 0, 0),
    ("HK-36965", 1, 2), ("HK-39301", 2, 2), ("HK-10990", 0, 0),
)
DATES = ("2026-09-23", "2026-10-15", "2026-11-14", "2026-12-31")


def build_queries(profiles):
    by_id = {p.id: p for p in profiles}
    queries = []
    for i, (ident, category, event) in enumerate(SEEDS):
        p = by_id[ident]
        query = dict(city=p.city, date=DATES[i % len(DATES)],
                     category=p.categories[category], event_type=p.event_formats[event],
                     budget_kzt=max(500000, (p.price_from_kzt or 0) * 2))
        if i % 3 == 0 and p.languages:
            query["language"] = p.languages[0]
        if i % 4 == 0 and p.max_hours:
            query["hours"] = min(4, p.max_hours)
        queries.append(query)
    return queries


def distinct(cards):
    """Exact text difference after removing all returned names; not semantic QA."""
    texts = []
    for card in cards:
        value = normalized(card["explanation"])
        for other in cards:
            value = re.sub(re.escape(normalized(other["name"])), "", value)
        texts.append(" ".join(value.split()))
    return all(a and b and a != b for a, b in combinations(texts, 2))


def share(numerator, denominator):
    return "{}/{} ({:.1%})".format(numerator, denominator, numerator / denominator) if denominator else "н/д (0 наблюдений)"


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def evaluate(profiles):
    rows = []
    for number, query in enumerate(build_queries(profiles), 1):
        runs, elapsed, errors = [], [], []
        for _ in range(2):
            # Cache hits would make both latency and explanation statistics misleading.
            explain._CACHE.clear()
            start = perf_counter()
            try:
                runs.append(match(query, profiles))
                errors.append(None)
            except Exception as exc:
                # Exception messages may contain credentials; record only the type.
                runs.append(None)
                errors.append(type(exc).__name__)
            elapsed.append(perf_counter() - start)
        rows.append(dict(query=query, runs=runs, elapsed=elapsed, errors=errors))
        print("Запрос {}/24: {}, {:.2f}/{:.2f} с".format(
            number, runs[0]["outcome"] if runs[0] else errors[0], *elapsed), flush=True)
    return rows


def write_report(rows, model, path):
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                         text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))
        commit += " (есть незакоммиченные изменения)" if dirty else ""
    except (OSError, subprocess.CalledProcessError):
        commit = "недоступен"
    cards = [c for row in rows if row["runs"][0] for c in row["runs"][0]["cards"]]
    sources = Counter()
    reasons = Counter()
    for card in cards:
        if card["explanation_source"] == "llm":
            sources["first" if card["explanation_attempts"] == 1 else "revised"] += 1
        else:
            sources["template"] += 1
            reasons[card.get("fallback_reason") or "Причина не указана"] += 1
    times = [t for row in rows for t in row["elapsed"]]
    errors = sum(e is not None for row in rows for e in row["errors"])
    stable = sum(all(row["runs"]) and
                 [c["id"] for c in row["runs"][0]["cards"]] ==
                 [c["id"] for c in row["runs"][1]["cards"]] for row in rows)
    eligible = [row["runs"][0]["cards"] for row in rows
                if row["runs"][0] and len(row["runs"][0]["cards"]) >= 2]
    different = sum(distinct(group) for group in eligible)
    average, maximum = sum(times) / len(times), max(times)
    lines = ["# Оценка качества объяснений", "",
             "Дата и время: " + datetime.now().astimezone().isoformat(timespec="seconds"),
             "", "Модель: " + cell(model), "", "Git: " + commit, "",
             "Данные: официальный data/hackathon-dataset-anonymized.csv. "
             "24 фиксированных запроса из полей каталога; каждый запущен дважды без кэша. "
             "Даты фиксированы, занятость не обходится; пустые результаты включены.", "",
             "Доли объяснений и число карточек считаются по первым запускам (повторы не удваивают выборку). "
             "Скорость учитывает все 48 вызовов match(), включая ошибки, без загрузки CSV. "
             "Различимость — неравенство нормализованных текстов после удаления имён; "
             "только ответы с ≥2 карточками, без утверждения о смысловой уникальности. "
             "Принятие AI означает прохождение проверщика приложения, а не независимую проверку фактов.", "",
             "| Метрика | Результат |", "|---|---|",
             "| Карточек (первые запуски) | {} |".format(len(cards)),
             "| AI принят с первой попытки | {} |".format(share(sources["first"], len(cards))),
             "| AI принят после исправления | {} |".format(share(sources["revised"], len(cards))),
             "| Шаблонный откат | {} |".format(share(sources["template"], len(cards))),
             "| Среднее / максимум match(), с | {:.3f} / {:.3f} |".format(average, maximum),
             "| Каждый вызов <10 с | {} |".format("да" if maximum < 10 else "нет"),
             "| Одинаковый порядок id | {} |".format(share(stable, len(rows))),
             "| Попарно различные объяснения | {} |".format(share(different, len(eligible))),
             "| Ошибки вызовов | {} |".format(errors), "",
             "## Причины шаблонного отката", "", "| Причина | Карточек |", "|---|---|"]
    lines += ["| {} | {} |".format(cell(reason), count) for reason, count in sorted(reasons.items())]
    if not reasons:
        lines.append("| Откатов не зарегистрировано | 0 |")
    lines += ["", "## Запросы", "",
              "| № | Город · дата · формат · категория · бюджет · язык · часы | Исход 1 / 2 | Карточек 1 / 2 | ID 1 / 2 | Секунд 1 / 2 |", "|---|---|---|---|---|---|"]
    for i, row in enumerate(rows, 1):
        q = row["query"]
        query = " · ".join(str(q.get(k, "—")) for k in
                           ("city", "date", "event_type", "category", "budget_kzt", "language", "hours"))
        outcomes = [r["outcome"] if r else "ошибка: " + e for r, e in zip(row["runs"], row["errors"])]
        counts = [str(len(r["cards"])) if r else "—" for r in row["runs"]]
        ids = [", ".join(c["id"] for c in r["cards"]) or "—" if r else "ошибка" for r in row["runs"]]
        lines.append("| {} | {} | {} | {} | {} | {:.3f} / {:.3f} |".format(
            i, cell(query), cell(" / ".join(outcomes)), " / ".join(counts),
            cell(" / ".join(ids)), *row["elapsed"]))
    summary = ("Карточек: {}; AI с первой попытки: {}; после исправления: {}; шаблон: {}. "
               "Среднее/максимум: {:.3f}/{:.3f} с; порядок совпал: {}. ").format(
        len(cards), share(sources["first"], len(cards)), share(sources["revised"], len(cards)),
        share(sources["template"], len(cards)), average, maximum, share(stable, len(rows)))
    conclusion = "Порог скорости соблюдён." if maximum < 10 else "Порог скорости нарушен: есть вызовы ≥10 с."
    if errors:
        conclusion += " Есть ошибки вызовов: {}.".format(errors)
    if not sources["first"] + sources["revised"]:
        conclusion += " Принятых AI-объяснений нет; качество LLM этим запуском не подтверждено."
    conclusion += " Это результат фиксированной выборки, а не гарантия для всех запросов; смысловая оценка требует ручного просмотра."
    lines += ["", "## Вывод", "", summary + conclusion, ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(summary + conclusion)
    print("Отчёт: " + str(path))
    return int(errors > 0 or maximum >= 10 or stable != len(rows))


def main():
    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY", "").strip() or not os.getenv("OPENAI_MODEL", "").strip():
        print("Оценка LLM пропущена: задайте OPENAI_API_KEY и OPENAI_MODEL в .env или окружении. "
              "Вызовы API не выполнялись; docs/EVAL.md не изменён.")
        return 0
    return write_report(evaluate(load_profiles(DEFAULT_PATH)), os.environ["OPENAI_MODEL"], ROOT / "docs/EVAL.md")


if __name__ == "__main__":
    sys.exit(main())
