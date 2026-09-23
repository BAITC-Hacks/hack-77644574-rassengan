"""Deterministic explanations; no network or personal account required."""


def template_explanation(card: dict) -> str:
    # TODO: add an LLM rewriter here, validating its schema and grounding in facts,
    # with timeout/retry handling and this deterministic template as fallback.
    facts = card["matched_facts"]
    return "; ".join(fact["text"] for fact in facts) + "."
