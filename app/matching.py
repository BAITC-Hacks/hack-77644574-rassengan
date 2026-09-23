"""Pure filtering/ranking. Each rejection counts only its first failing rule."""
import re
from datetime import date as Date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.data import Contractor
from app.explain import template_explanation


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
        if Date.fromisoformat(value).isoformat() != value:
            raise ValueError("Use YYYY-MM-DD")
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


def match(request, profiles: List[Contractor]) -> dict:
    req = request if isinstance(request, MatchRequest) else MatchRequest.model_validate(request)
    candidates = [p for p in profiles if p.city == req.city and req.category in p.categories]
    counts = dict.fromkeys(REASONS, 0)
    result = {"outcome": "no_category_in_city", "cards": [], "rejection_counts": counts,
              "candidate_count": len(candidates), "passing_count": 0,
              "message": "В этом городе такой категории нет.", "why_fewer_than_3": None}
    if not candidates:
        return result
    cards = []
    keywords = _tokens(" ".join([req.event_type, req.category, req.city, req.language or ""]))
    for p in candidates:
        failures = [req.date in p.busy_dates, req.event_type not in p.event_formats,
                    p.price_from_kzt is not None and p.price_from_kzt > req.budget_kzt,
                    req.hours is not None and p.max_hours is not None and p.max_hours < req.hours,
                    req.language is not None and req.language not in p.languages]
        reason = next((key for key, failed in zip(REASONS, failures) if failed), None)
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
        # A contiguous excerpt from the first sentence, never a generated claim.
        quote = re.split(r"[.!?\n]", p.description.strip(), maxsplit=1)[0][:140]
        if quote:
            fact("description", "из описания: «" + quote + ("…" if len(quote) < len(re.split(r"[.!?\n]", p.description.strip(), maxsplit=1)[0]) else "") + "»")
        # Price closeness: 0..100; language: 10; headroom: 0..5; overlap: 0..5.
        price_score = 0 if p.price_from_kzt is None else 100 * (p.price_from_kzt / req.budget_kzt if req.budget_kzt else 1)
        headroom = min((p.max_hours - req.hours) / req.hours, 1) * 5 if req.hours is not None and p.max_hours is not None else 0
        overlap = len(keywords & _tokens(p.description)) / max(len(keywords), 1) * 5
        card = {"id": p.id, "name": p.anon_name, "category": req.category, "city": p.city,
                "price_from_kzt": p.price_from_kzt, "price_unknown": p.price_from_kzt is None,
                "synthetic": p.synthetic, "city_imputed": p.city_imputed, "price_imputed": p.price_imputed,
                "score": round(price_score + (10 if req.language else 0) + headroom + overlap, 8),
                "matched_facts": facts}
        card["explanation"] = template_explanation(card)
        cards.append(card)
    cards.sort(key=lambda card: (-card["score"], card["id"]))
    result.update(outcome="found" if cards else "no_match", cards=cards[:3], passing_count=len(cards),
                  message="Подобрали подрядчиков." if cards else "Кандидаты есть, но ни один не проходит по условиям.")
    if len(cards) < 3:
        rejected = "; ".join(text + ": " + str(counts[key]) for key, text in REASONS.items() if counts[key])
        result["why_fewer_than_3"] = "Подходит " + str(len(cards)) + " из " + str(len(candidates)) + " кандидатов: " + (rejected or "в городе для этой категории всего " + str(len(candidates)) + " профилей") + "."
    return result
