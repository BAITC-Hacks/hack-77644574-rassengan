"""Deterministic hard filters followed by an additive, explainable score.

Exact weights (points): description event stem/synonym match: 40; category
word/stem coverage: 20 * matched category words / category words.
Language: 10 for requested supported language; without a language request,
2 for two or more distinct languages, otherwise 0.
Hours: 5 * min((max_hours - requested_hours) / requested_hours, 1);
0 when hours are not requested or the profile has no hours limit.
Value: 5 * (1 - price / budget), or 5 for zero price and zero budget;
unknown price: -2. Only profiles passing the budget filter are scored.
Data quality: -1 each for price_imputed, city_imputed and synthetic.
Components are rounded to 8 decimals and summed; ties sort by ascending id.
Each rejection counts only its first failing rule (busy, format, budget,
hours, language). Trace includes all city/category candidates, sorted by id.
"""
import re
from datetime import date as Date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

from app.data import CALENDAR_END, CALENDAR_START, Contractor
from app.explain import apply_explanations
from app.snippets import clauses


class MatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    city: str = Field(min_length=1)
    date: str
    event_type: str = Field(min_length=1)
    category: str = Field(min_length=1)
    budget_kzt: int = Field(ge=0)
    hours: Optional[float] = Field(default=None, gt=0, allow_inf_nan=False)
    language: Optional[str] = Field(default=None, min_length=1)

    @field_validator("date")
    @classmethod
    def valid_date(cls, value: str) -> str:
        parsed = Date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError("Use YYYY-MM-DD")
        if not CALENDAR_START <= parsed <= CALENDAR_END:
            raise PydanticCustomError(
                "calendar_range",
                "Календарь занятости покрывает только "
                f"{CALENDAR_START:%d.%m.%Y}–{CALENDAR_END:%d.%m.%Y}; "
                "выберите дату в этом диапазоне.",
            )
        return value


REASONS = {
    "busy": "заняты на выбранную дату",
    "event_format": "не принимают этот формат",
    "budget": "цена выше бюджета",
    "hours": "недостаточная длительность работы",
    "language": "не поддерживают нужный язык",
}


def _tokens(value: str):
    return set(re.findall(r"[а-яёa-z0-9]+", value.casefold()))


def _money(value: int) -> str:
    return format(value, ",").replace(",", " ") + " ₸"


EVENT_STEMS = {
    "свадьба": ("свадеб", "свадьб", "wedding"),
    "той": ("той", "тоев"),
    "корпоратив": ("корпоратив", "корпорат"),
    "конференция": ("конференц", "форум"),
    "юбилей": ("юбиле",),
    "день рождения": ("день рождения", "дня рождения", "др", "birthday"),
}
CATEGORY_STEMS = {
    "ведущий": ("ведущ", "ведени", "тамада"),
    "фотограф": ("фотограф", "фотосъем", "фотосъём"),
    "флорист": ("флорист", "цветоч"),
    "банкетный": ("банкет",),
    "декоратор": ("декор", "оформлен"),
    "отель": ("отел", "гостиниц", "hotel"),
}


def dataset_options(profiles):
    return {
        "cities": sorted({p.city for p in profiles}),
        "categories": sorted({v for p in profiles for v in p.categories}),
        "event_formats": sorted({v for p in profiles for v in p.event_formats}),
        "languages": sorted({v for p in profiles for v in p.languages}),
    }


def _key(value):
    return value.strip().casefold()


def _canonical(value, options):
    return next((v for v in options if _key(v) == _key(value)), value.strip())


def _mentions(description, stems):
    # Word boundary prevents short synonyms such as «др» matching «другой».
    return any(re.search(r"(?<!\w)" + re.escape(stem) + (r"(?!\w)" if stem == "др" else ""), description.casefold()) for stem in stems)


def _score(req, p):
    words = _tokens(req.category) - {"и"}
    relevance = 40 if _mentions(p.description, EVENT_STEMS.get(_key(req.event_type), (_key(req.event_type),))) else 0
    coverage = sum(_mentions(p.description, CATEGORY_STEMS.get(word, (word,))) for word in words)
    language = 10 if req.language else (2 if len({_key(v) for v in p.languages}) > 1 else 0)
    hours = 5 * min((p.max_hours - req.hours) / req.hours, 1) if req.hours is not None and p.max_hours is not None else 0
    value = -2 if p.price_from_kzt is None else 5 * (1 - p.price_from_kzt / req.budget_kzt) if req.budget_kzt else 5
    return {key: round(value, 8) for key, value in {
        "event_relevance": relevance,
        "category_relevance": 20 * coverage / max(len(words), 1),
        "language": language, "hours_headroom": hours, "value_for_money": value,
        "data_quality": -sum((p.price_imputed, p.city_imputed, p.synthetic)),
    }.items()}


def _reason_text(key, req, count):
    one = count % 10 == 1 and count % 100 != 11
    return {
        "busy": ("занят" if one else "заняты") + " на " + Date.fromisoformat(req.date).strftime("%d.%m.%Y"),
        "event_format": ("не берёт" if one else "не берут") + " формат «" + req.event_type + "»",
        "budget": "с ценой выше бюджета",
        "hours": "с недостаточной длительностью работы",
        "language": ("не поддерживает" if one else "не поддерживают") + " язык «" + (req.language or "") + "»",
    }[key]


def match(request, profiles: List[Contractor]) -> dict:
    req = request if isinstance(request, MatchRequest) else MatchRequest.model_validate(request)
    options = dataset_options(profiles)
    req = req.model_copy(update={
        field: _canonical(getattr(req, field), options[option])
        for field, option in (("city", "cities"), ("category", "categories"),
                              ("event_type", "event_formats"), ("language", "languages"))
        if getattr(req, field) is not None
    })
    candidates = sorted([p for p in profiles if _key(p.city) == _key(req.city)
                         and any(_key(c) == _key(req.category) for c in p.categories)], key=lambda p: p.id)
    counts = dict.fromkeys(REASONS, 0)
    available_cities = sorted({p.city for p in profiles if any(_key(c) == _key(req.category) for c in p.categories)})
    result = {"outcome": "no_category_in_city", "cards": [], "rejection_counts": counts,
              "candidate_count": len(candidates), "passing_count": 0, "trace": [],
              "request": req.model_dump(), "available_cities": available_cities,
              "message": "В городе " + req.city + " нет подрядчиков категории " + req.category,
              "why_fewer_than_3": None, "explainer": "template"}
    if not candidates:
        result["message"] += (". Эта категория есть в городах: " + ", ".join(available_cities) + "."
                              if available_cities else ". В каталоге этой категории нет.")
        result["why_fewer_than_3"] = result["message"]
        return result
    cards = []
    for p in candidates:
        failures = [req.date in p.busy_dates, not any(_key(req.event_type) == _key(v) for v in p.event_formats),
                    p.price_from_kzt is not None and p.price_from_kzt > req.budget_kzt,
                    req.hours is not None and p.max_hours is not None and p.max_hours < req.hours,
                    req.language is not None and not any(_key(req.language) == _key(v) for v in p.languages)]
        reason = next((key for key, failed in zip(REASONS, failures) if failed), None)
        trace = {"id": p.id, "name": p.anon_name, "status": "rejected" if reason else "passed",
                 "reason": _reason_text(reason, req, 1) if reason else None, "score": None}
        result["trace"].append(trace)
        if reason:
            counts[reason] += 1
            continue
        facts = []

        def fact(kind, text):
            facts.append({"kind": kind, "text": text})

        fact("availability", "по календарю свободен на " + req.date)
        fact("format", "принимает формат «" + req.event_type + "»")
        if p.price_from_kzt is None:
            fact("price", "цена не указана: соответствие бюджету " + _money(req.budget_kzt) + " требует подтверждения")
        else:
            fact("price", "цена от " + _money(p.price_from_kzt) + " при бюджете " + _money(req.budget_kzt))
        if req.language:
            fact("language", "язык работы — " + req.language)
        if req.hours is not None:
            if p.max_hours is None:
                fact("hours", "лимит часов не указан; запрошено " + format(req.hours, "g") + " ч")
            else:
                fact("hours", "работает до " + format(p.max_hours, "g") + " ч при запросе " + format(req.hours, "g") + " ч")
        # Prefer an event-relevant sentence; keep a contiguous, word-complete quote.
        sentences = [part.strip() for part in re.split(r"[.!?\n]", p.description) if part.strip()]
        stems = EVENT_STEMS.get(_key(req.event_type), (_key(req.event_type),))
        sentence = next((part for part in sentences if _mentions(part, stems)),
                        sentences[0] if sentences else "")
        quote = sentence[:140]
        if len(sentence) > 140 and " " in quote:
            quote = quote.rsplit(" ", 1)[0]
        if quote:
            fact("description", "из описания: «" + quote + ("…" if len(quote) < len(sentence) else "") + "»")
        breakdown = _score(req, p)
        if breakdown["event_relevance"] > 0:
            matched = next((part for part in clauses(p.description) if _mentions(part, stems)), p.description)
            # Keep the matching word in the window, even in a long description.
            words = list(re.finditer(r"\S+", matched))
            hit = next((i for i, word in enumerate(words) if _mentions(matched[word.start():], stems)
                        and (i == len(words) - 1 or not _mentions(matched[words[i + 1].start():], stems))), 0)
            start = 0 if len(matched) <= 90 else words[max(0, hit - 3)].start() if words else 0
            snippet = matched[start:start + 90]
            if start + 90 < len(matched):
                snippet = snippet.rsplit(" ", 1)[0]
            facts.append({"kind": "rank_reason", "component": "event_relevance",
                          "text": "Совпадение формата в описании: «" + snippet + "»",
                          "snippet": snippet, "complete": snippet == matched})
        if breakdown["category_relevance"] > 0:
            matched_words = sorted({word.group() for word in re.finditer(r"[а-яёa-z]+", p.description, re.I)
                if any(_mentions(word.group(), CATEGORY_STEMS.get(token, (token,)))
                       for token in _tokens(req.category) - {"и"})})
            facts.append({"kind": "rank_reason", "component": "category_relevance",
                          "text": "Категория подтверждается словами: «" + ", ".join(matched_words) + "»"})
        for component, kind in (("language", "language"), ("hours_headroom", "hours")):
            if breakdown[component] > 0:
                text = next((f["text"] for f in facts if f["kind"] == kind), None)
                if text is None and kind == "language":
                    text = "Языки работы: " + ", ".join(p.languages)
                if text:
                    facts.append({"kind": "rank_reason", "component": component, "text": text})
        card = {"id": p.id, "name": p.anon_name, "category": req.category, "city": p.city,
                "price_from_kzt": p.price_from_kzt, "price_unknown": p.price_from_kzt is None,
                "synthetic": p.synthetic, "city_imputed": p.city_imputed, "price_imputed": p.price_imputed,
                "score": round(sum(breakdown.values()), 8), "score_breakdown": breakdown,
                "matched_facts": facts}
        cards.append(card)
        trace["score"] = card["score"]
    cards.sort(key=lambda card: (-card["score"], card["id"]))
    _add_distinct_facts(cards[:3], {p.id: p for p in candidates})
    result["explainer"] = apply_explanations(req.model_dump(), cards[:3])
    rejected = ", ".join(str(counts[key]) + " " + _reason_text(key, req, counts[key])
                         for key in REASONS if counts[key])
    result.update(outcome="found" if cards else "no_match", cards=cards[:3], passing_count=len(cards),
                  message="Подобрали " + str(min(len(cards), 3)) + " подрядчиков" if cards else
                  "Кандидаты есть (" + str(len(candidates)) + "), но ни один не проходит по условиям: " + rejected + ".")
    if len(cards) < 3:
        result["why_fewer_than_3"] = ("Подходит " if len(cards) == 1 else "Подходят ") + str(len(cards)) + " из " + str(len(candidates)) + " кандидатов"
        result["why_fewer_than_3"] += (": " + rejected if rejected else "") + "."
        if len(candidates) < 3:
            noun = "профиль" if len(candidates) == 1 else "профиля"
            result["why_fewer_than_3"] += " В городе " + req.city + " в категории «" + req.category + "» всего " + str(len(candidates)) + " " + noun + "."
    return result


def _norm_text(text):
    return " ".join(text.casefold().replace("ё", "е").split())


def _add_distinct_facts(top, by_id):
    """DoD2: give each shown card a clause of its own full description that the other shown cards lack.

    Uses only catalogue text (no invented differences). Brand names and praise do not count as a
    difference; clauses with numbers or several concrete words are preferred.
    """
    if len(top) < 2:
        return
    def core(text):
        text = re.sub(r"«[^»]*»|[A-Za-z][A-Za-z'’\-]*|[^\w\s-]", " ", text)
        return _norm_text(text)
    praise = re.compile(r"идеальн|незабываем|отличн|лучш|профессионал|уникальн|любовь|\bменя зовут\b", re.I)
    descriptions = {card["id"]: by_id[card["id"]].description or "" for card in top}
    for card in top:
        others = " ".join(core(descriptions[c["id"]]) for c in top if c is not card)
        best, best_score = None, -1
        for part in clauses(descriptions[card["id"]]):
            words = core(part).split()
            has_digit = bool(re.search(r"\d", part))
            if praise.search(part) or not words or core(part) in others:
                continue
            if len(words) < 3 and not has_digit:
                continue
            score = (2 if has_digit else 0) + min(len(words), 8) / 8
            if score > best_score:
                best, best_score = part, score
        if best:
            best = " ".join(re.sub(r"[^\w\s«»,.:;!?()\-–—]", " ", best).split())
            quote = best[:120]
            if len(best) > 120 and " " in quote:
                quote = quote.rsplit(" ", 1)[0]
            card["matched_facts"].append({"kind": "distinct", "text": "отличие в описании: «" + quote + "»"})
