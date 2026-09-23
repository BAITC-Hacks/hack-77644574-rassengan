"""Deterministic fallback and cached, independently checked LLM explanations."""
import hashlib
import json
import logging
import math
import os
import re
from threading import Lock
from time import monotonic

from app.llm import explain_cards, revise_explanations, _description_for_event
from app.explain_check import normalized, validate
from app.snippets import short_clause, clauses

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
    for part in clauses(text):
        if re.search(r"\bменя зовут\b", part, re.I):
            continue
        if re.fullmatch(r"Я\s*[—–-]\s*[А-ЯЁA-Z][а-яёa-z]+(?:\s+[А-ЯЁA-Z][а-яёa-z]+){0,3}", part):
            continue
        quote = short_clause(part, limit)
        if quote:
            return quote
    return ""


def _distinguishing_fact(card, others):
    facts = _facts(card)
    reason = next((f for f in card["matched_facts"] if f["kind"] == "rank_reason"
                   and f.get("component") == "event_relevance" and f.get("complete")), None)
    price = card.get("price_from_kzt")
    if others and price is not None and all(
            c.get("price_from_kzt") is not None and price < c["price_from_kzt"] for c in others):
        return "Начальная цена ниже, чем у остальных показанных вариантов"
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
    distinct = re.search(r"«(.*)»", facts.get("distinct", ""))
    if distinct:
        return "Отличие от других вариантов в описании: «" + distinct.group(1) + "»"
    # Identical or missing descriptions cannot justify an invented distinction.
    if "language" in facts:
        return "У подрядчика " + facts["language"].replace("; ", ", ")
    return "Подрядчик " + facts.get("hours", facts["format"]).replace("; ", ", ")


def template_explanation(card: dict, cards=None, force_distinct=False) -> str:
    others = [c for c in (cards or []) if c["id"] != card["id"]]
    distinct = re.search(r"«(.*)»", _facts(card).get("distinct", ""))
    if force_distinct and distinct:
        lead = "Отличие от других вариантов в описании: «" + distinct.group(1) + "»"
    else:
        lead = _distinguishing_fact(card, others)
    description = _description(card)
    # Quote the factual experience clause instead of preceding marketing praise.
    experience = re.search(r"опыт\w* (?:более )?\d+ (?:лет|год\w*)", description, re.I)
    if experience and "самых" in description[:experience.start()]:
        description = description[experience.start():]
    quote = _short_quote(description)
    rank_quote = next((_short_quote(f["snippet"]) for f in card["matched_facts"] if f["kind"] == "rank_reason"
                       and f.get("component") == "event_relevance" and f.get("complete")
                       and _short_quote(f["snippet"])), "")
    quote = rank_quote or quote
    price = _facts(card)["price"]
    tail = "В описании: «" + quote + "», " + price if quote and quote not in lead else "Для вашего бюджета: " + price
    for kind in ("language", "hours"):
        requirement = _facts(card).get(kind)
        if requirement and requirement not in lead:
            tail += ", " + requirement.replace("; ", ", ")
    tail = tail[0].upper() + tail[1:]
    return lead + ". " + tail + "."


def _generate_verified(request, cards):
    try:
        timeout = float(os.getenv("LLM_TIMEOUT_S", "8"))
    except ValueError:
        timeout = 8
    if not math.isfinite(timeout) or timeout <= 0:
        timeout = 8
    deadline = monotonic() + timeout
    try:
        output = explain_cards(request, cards, timeout)
    except Exception as exc:
        logging.getLogger(__name__).warning("Explainer unavailable (%s)", type(exc).__name__)
        output = None
    now = monotonic()
    if now > deadline:
        # A late answer breaks the response-time budget: use templates instead.
        output = None
    results, rejected, previous = {}, [], []
    for card in cards:
        text = output.get(card["id"]) if isinstance(output, dict) else None
        ok, reason = validate(text, dict(card, request=request), previous) if text is not None else (
            False, "AI недоступен или не вернул объяснение: проверьте настройки и журнал")
        result = {"explanation": text if ok else template_explanation(card, cards),
                  "explanation_source": "llm" if ok else "template", "explanation_attempts": 1}
        if not ok:
            result["fallback_reason"] = reason
            if isinstance(text, str):
                rejected.append({"id": card["id"], "text": text, "reason": reason})
        results[card["id"]] = result
        previous.append(result["explanation"])
    remaining = deadline - now
    if rejected and remaining >= 1.5:
        try:
            revised = revise_explanations(request, cards, rejected, remaining)
        except Exception as exc:
            logging.getLogger(__name__).warning("Revision unavailable (%s)", type(exc).__name__)
            revised = None
        # Reject a late response as well; never start another attempt.
        if monotonic() > deadline:
            revised = None
        rejected_ids = {row["id"] for row in rejected}
        for card in cards:
            if card["id"] not in rejected_ids:
                continue
            result = results[card["id"]]
            result["explanation_attempts"] = 2
            text = revised.get(card["id"]) if isinstance(revised, dict) else None
            others = [value["explanation"] for ident, value in results.items() if ident != card["id"]]
            ok, reason = validate(text, dict(card, request=request), others) if text is not None else (
                False, "AI не вернул исправленное объяснение: проверьте настройки и журнал")
            if ok:
                result.update(explanation=text, explanation_source="llm")
                result.pop("fallback_reason", None)
            else:
                result["fallback_reason"] = reason
    _dedupe_templates(cards, results)
    return results


def _dedupe_templates(cards, results):
    """DoD2 safeguard: template texts of one response must differ even with names removed."""
    seen = {}
    for card in cards:
        result = results[card["id"]]
        key = normalized(result["explanation"].replace(card.get("name", ""), ""))
        if key in seen and result["explanation_source"] == "template":
            result["explanation"] = template_explanation(card, cards, force_distinct=True)
            key = normalized(result["explanation"].replace(card.get("name", ""), ""))
        seen[key] = card["id"]


def apply_explanations(request, cards):
    if not cards:
        return "template"
    # Cache only final checked results; do not include prior explanation metadata.
    inputs = [{k: v for k, v in c.items() if k not in (
        "explanation", "explanation_source", "explanation_attempts", "fallback_reason")} for c in cards]
    key = hashlib.sha256(json.dumps([request, inputs], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    with _CACHE_LOCK:
        if key not in _CACHE:
            _CACHE[key] = _generate_verified(request, cards)
        for card in cards:
            card.pop("fallback_reason", None)
            card.update(_CACHE[key][card["id"]])
    sources = {c["explanation_source"] for c in cards}
    return next(iter(sources)) if len(sources) == 1 else "mixed"
