"""Conservative lexical checks, not a claim of semantic verification."""
import json
import re
from decimal import Decimal
from difflib import SequenceMatcher

BANNED = ("отличный выбор", "идеально подойдет", "лучший выбор", "не пожалеете",
          "для вашего мероприятия", "прекрасный вариант", "высокий профессионализм")
STOP_WORDS = {"этот", "этого", "также", "работает", "работы", "мероприятия", "мероприятий", "описания", "который"}


def normalized(text):
    return " ".join(text.casefold().replace("ё", "е").split())


def numbers(text):
    # Grouped thousands (including NBSP) and decimal hours are single numbers.
    return {Decimal(re.sub(r"\s", "", n).replace(",", ".")) for n in
            re.findall(r"(?<!\w)\d+(?:[ \u00a0\u202f]\d{3}(?!\d))*(?:[.,]\d+)?", text)}


def sentence_count(text):
    return len([part for part in re.split(r"(?<!\d)[.!?]+|[.!?]+(?!\d)", text) if part.strip(' \n\t»”"')])


def validate(text, card, other_texts):
    if not isinstance(text, str) or not text.strip():
        return False, "Пустое объяснение"
    if len(text) > 400:
        return False, "Объяснение длиннее 400 символов"
    if sentence_count(text) > 2:
        return False, "Больше двух предложений"
    value = normalized(text)
    if any(phrase in value for phrase in BANNED):
        return False, "Общая рекламная фраза"
    facts = card.get("matched_facts", [])
    allowed = numbers(json.dumps({"facts": facts, "request": card.get("request", {})}, ensure_ascii=False))
    if numbers(text) - allowed:
        return False, "Число не подтверждено фактами"
    concrete = False
    for fact in facts:
        source = normalized(fact["text"])
        if fact["kind"] == "price":
            concrete |= bool(numbers(text) & numbers(source))
        elif fact["kind"] == "format":
            concrete |= any(normalized(quote) in value for quote in re.findall("«([^»]+)»", source))
        elif fact["kind"] == "language":
            concrete |= source.split("—")[-1].strip() in value
        elif fact["kind"] == "description":
            words = set(re.findall(r"[а-яa-z]{4,}", source)) - STOP_WORDS
            concrete |= bool(words & set(re.findall(r"[а-яa-z]{4,}", value)))
    if not concrete:
        return False, "Нет конкретного факта карточки"
    if any(SequenceMatcher(None, value, normalized(other)).ratio() > 0.8 for other in other_texts):
        return False, "Объяснение слишком похоже на другую карточку"
    return True, ""
