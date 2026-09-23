"""Deterministic fallback and cached, independently checked LLM explanations."""
import hashlib
import json
import logging
import math
import os
import re
from threading import Lock

from app.llm import explain_cards, _description_for_event
from app.explain_check import normalized, validate
from app.snippets import short_clause

_CACHE = {}
_CACHE_LOCK = Lock()


def _facts(card):
    return {f["kind"]: f["text"] for f in card["matched_facts"]}


def _description(card):
    facts = _facts(card)
    description = facts.get("description", "")
    event = re.search(r"«([^»]+)»", facts.get("format", ""))
    if event:
        description = _description_for_event(description, event.group(1), card.get("city")) or ""
    quote = re.search(r"«(.*)»", description)
    return quote.group(1) if quote else ""


def _short_quote(text, limit=90):
    return short_clause(text, limit)


def _distinguishing_fact(card, others):
    facts = _facts(card)
    reason = next((f for f in card["matched_facts"] if f["kind"] == "rank_reason"
                   and f.get("component") == "event_relevance" and f.get("complete")), None)
    price = card.get("price_from_kzt")
    if others and price is not None and all(
            c.get("price_from_kzt") is not None and price < c["price_from_kzt"] for c in others):
        return "Самая низкая начальная цена среди показанных вариантов"
    if (others and card.get("score_breakdown", {}).get("event_relevance", 0) > 0
            and all(c.get("score_breakdown", {}).get("event_relevance") == 0 for c in others)):
        return "Только в этом описании упоминается запрошенный формат: " + ("«" + _short_quote(reason["snippet"]) + "»" if reason and _short_quote(reason["snippet"]) else facts["format"])
    if reason and _short_quote(reason["snippet"]):
        return "Совпадение с форматом в описании: «" + _short_quote(reason["snippet"]) + "»"
    for kind in ("language", "hours"):
        if kind in facts and all(_facts(c).get(kind) != facts[kind] for c in others):
            return facts[kind][0].upper() + facts[kind][1:].replace("; ", ", ")
    description = _description(card)
    experience = re.search(r"опыт\w*(?: ведения \w+)? (?:более )?\d+ (?:лет|год\w*)", description, re.I)
    if experience and all(normalized(experience.group()) not in normalized(_description(c)) for c in others):
        return "В описании указан " + re.sub(r"^опыт\w*", "опыт", experience.group(), flags=re.I)
    # Prefer a short clause absent from the other returned descriptions.
    clauses = re.split(r"[,;]", description.split(":", 1)[-1])
    for clause in clauses:
        clause = clause.strip()
        if (len(clause.split()) >= 2 and _short_quote(clause) and card.get("name", "") not in clause
                and all(normalized(clause) not in normalized(_description(c)) for c in others)):
            return "В описании отдельно отмечено: «" + _short_quote(clause) + "»"
    # Identical or missing descriptions cannot justify an invented distinction.
    return "По данным карточки " + facts.get("language", facts.get("hours", facts["format"])).replace("; ", ", ")


def template_explanation(card: dict, cards=None) -> str:
    others = [c for c in (cards or []) if c["id"] != card["id"]]
    lead = _distinguishing_fact(card, others)
    description = _description(card)
    # Quote the factual experience clause instead of preceding marketing praise.
    experience = re.search(r"опыт\w* (?:более )?\d+ (?:лет|год\w*)", description, re.I)
    if experience and "самых" in description[:experience.start()]:
        description = description[experience.start():]
    quote = _short_quote(description)
    rank_quote = next((f["snippet"] for f in card["matched_facts"] if f["kind"] == "rank_reason"
                       and f.get("component") == "event_relevance" and f.get("complete")
                       and _short_quote(f["snippet"])), "")
    quote = rank_quote or quote
    price = _facts(card)["price"]
    tail = "В профиле: «" + quote + "», " + price if quote and quote not in lead else "По условиям карточки " + price
    for kind in ("language", "hours"):
        requirement = _facts(card).get(kind)
        if requirement and requirement not in lead:
            tail += ", " + requirement.replace("; ", ", ")
    tail = tail[0].upper() + tail[1:]
    return lead + ". " + tail + "."


def apply_explanations(request, cards):
    if not cards:
        return "template"
    # Include facts as well as ids to avoid stale text if the catalogue changes.
    key = hashlib.sha256(json.dumps([request, [(c["id"], c["matched_facts"]) for c in cards]],
                                    ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    with _CACHE_LOCK:
        if key not in _CACHE:
            try:
                timeout = float(os.getenv("LLM_TIMEOUT_S", "8"))
                if not math.isfinite(timeout) or timeout <= 0:
                    timeout = 8
                output = explain_cards(request, cards, timeout)
            except Exception as exc:
                logging.getLogger(__name__).warning("Explainer unavailable (%s)", type(exc).__name__)
                output = None
            _CACHE[key] = output
        output = _CACHE[key]
    previous = []
    for card in cards:
        text = output.get(card["id"]) if isinstance(output, dict) else None
        ok, reason = validate(text, dict(card, request=request), previous) if text is not None else (
            False, "AI недоступен или не вернул объяснение: проверьте настройки и журнал")
        card["explanation"] = text if ok else template_explanation(card, cards)
        card["explanation_source"] = "llm" if ok else "template"
        if not ok:
            card["fallback_reason"] = reason
        previous.append(card["explanation"])
    sources = {c["explanation_source"] for c in cards}
    return next(iter(sources)) if len(sources) == 1 else "mixed"
