"""Offline acceptance checks against the official catalogue: python scripts/demo.py."""
import os
from pathlib import Path
import re
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pydantic import ValidationError
from app.data import DEFAULT_PATH, load_profiles
from app import explain
from app.explain_check import BANNED, normalized, sentence_count
from app.matching import match


def main():
    # Override even inherited credentials; never load .env in the offline demo.
    os.environ["OPENAI_API_KEY"] = ""
    os.environ["OPENAI_MODEL"] = ""
    explain._CACHE.clear()
    profiles = load_profiles(DEFAULT_PATH)
    checks = []
    timings = []

    def check(label, ok, expected, actual):
        checks.append(bool(ok))
        print(("✅ " if ok else "❌ ") + label + (
            "" if ok else " (ожидалось {}, получено {})".format(expected, actual)))

    def run(label, **changes):
        request = dict(city="Алматы", date="2026-10-15", event_type="свадьба",
                       category="Ведущий", budget_kzt=1000000)
        request.update(changes)
        explain._CACHE.clear()
        start = perf_counter()
        try:
            return match(request, profiles)
        finally:
            timings.append((label, perf_counter() - start))

    print("Проверка основного сценария · официальный CSV · шаблонный режим")
    first = run("Сценарий 1")
    names = [c["name"] for c in first["cards"]]
    check("1. Плотная категория: три карточки в нужном порядке",
          first["outcome"] == "found" and names == ["Кики", "Эмилия", "Сон Гоку"],
          "found: Кики, Эмилия, Сон Гоку", (first["outcome"], names))
    second = run("Сценарий 2", date="2026-10-16")
    names2 = [c["name"] for c in second["cards"]]
    check("2. Другая дата: другая выдача", second["outcome"] == "found"
          and names2 == ["Хаул", "Мицури Канроджи"] and names2 != names,
          "found: Хаул, Мицури Канроджи", (second["outcome"], names2))
    for name in ("Кики", "Эмилия", "Сон Гоку"):
        trace = next((t for t in second["trace"] if t["name"] == name), {})
        check("Занятость: " + name, trace.get("status") == "rejected"
              and trace.get("reason") == "занят на 16.10.2026",
              "rejected: занят на 16.10.2026", trace)
    rare = run("Сценарий 3", category="Флорист", budget_kzt=500000)
    check("3. Редкая категория: два профиля и причина", rare["outcome"] == "found"
          and len(rare["cards"]) == 2 and "2 профиля" in (rare["why_fewer_than_3"] or ""),
          "found, 2 карточки, причина: 2 профиля",
          (rare["outcome"], len(rare["cards"]), rare["why_fewer_than_3"]))
    absent = run("Сценарий 4", city="Астана", category="Декоратор")
    check("4. Нет категории в городе: указан Алматы",
          absent["outcome"] == "no_category_in_city" and not absent["cards"]
          and "Алматы" in absent["available_cities"] and "Алматы" in absent["message"],
          "no_category_in_city, Алматы", (absent["outcome"], absent["message"]))
    expensive = run("Сценарий 5", category="Декоратор")
    check("5. Никто не проходит по бюджету", expensive["outcome"] == "no_match"
          and not expensive["cards"] and expensive["rejection_counts"]["budget"] == 3
          and "3 с ценой выше бюджета" in expensive["message"],
          "no_match, 3 с ценой выше бюджета", (expensive["outcome"], expensive["message"]))
    ids = [[c["id"] for c in r["cards"]] for r in
           (first, run("Повтор 2"), run("Повтор 3"))]
    check("Детерминизм: три запуска", ids[0] == ids[1] == ids[2], "одинаковые id", ids)
    for date in ("2026-09-23", "2026-12-31", "2026-09-22", "2027-01-01"):
        accepted = date in ("2026-09-23", "2026-12-31")
        try:
            run("Календарь " + date, date=date)
        except ValidationError as exc:
            errors = exc.errors()
            ok = not accepted and any(e["type"] == "calendar_range" and e["msg"] == (
                "Календарь занятости покрывает только 23.09.2026–31.12.2026; "
                "выберите дату в этом диапазоне.") for e in errors)
            actual = [e["msg"] for e in errors]
        else:
            ok, actual = accepted, "дата принята"
        check("Календарь: " + date, ok,
              "дата принята" if accepted else "отказ с сообщением о календаре", actual)
    texts = []
    for card in first["cards"]:
        text = card["explanation"]
        value = normalized(text)
        for name in names:
            value = re.sub(re.escape(normalized(name)), "", value)
        texts.append(" ".join(value.split()))
        check("Объяснение: " + card["name"], bool(text.strip()) and sentence_count(text) <= 2
              and not any(p in normalized(text) for p in BANNED),
              "1–2 предложения без общих фраз", text)
    check("Объяснения различаются без имён", len(set(texts)) == len(texts) == 3,
          "3 разных текста", texts)
    for label, elapsed in timings:
        check("Скорость: {} — {:.3f} с".format(label, elapsed), elapsed < 1,
              "< 1 с", "{:.3f} с".format(elapsed))
    failed = len(checks) - sum(checks)
    print("Итого: {} проверок, успешно {}, ошибок {}.".format(len(checks), sum(checks), failed))
    return int(failed > 0)


if __name__ == "__main__":
    sys.exit(main())
