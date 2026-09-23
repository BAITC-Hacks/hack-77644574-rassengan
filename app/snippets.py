"""Conservative, source-preserving clauses for short explanation quotes."""
import re


def clauses(text):
    # A trailing ellipsis marks an already truncated source, not a complete clause.
    parts = re.split(r"(?<!\d)[.!?;,:\n]+|[.!?;,:\n]+(?!\d)|\s+…\s+|(?<=лет)\s+(?=[А-Я])", text)
    return [part.strip() for part in parts if part.strip() and not part.strip().endswith("…")
            and not re.search(r"привет|здравств|дорогие друзья|добрый (день|вечер)", part, re.I)]


def short_clause(text, limit=90):
    for part in clauses(text):
        if len(part) <= limit and not re.search(r"\b(в|на|с|и|для|по|\w+(?:ной|ней|ской|ским|ного|ному))$", part, re.I):
            return part
    return ""
