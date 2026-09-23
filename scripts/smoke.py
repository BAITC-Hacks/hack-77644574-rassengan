"""Check that each provider's key and endpoint work.

Setup:  pip install anthropic openai python-dotenv
Run:    python scripts/smoke.py
Values come from the environment or a local .env file (see .env.example).
Model names and the NVIDIA base URL come from the organizers' sheet.
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PROMPT = "Reply with the single word: ready"


def claude():
    from anthropic import Anthropic

    client = Anthropic()  # reads ANTHROPIC_API_KEY
    r = client.messages.create(
        model=os.getenv("CLAUDE_MODEL", "claude-opus-5-5"),
        max_tokens=200,
        messages=[{"role": "user", "content": PROMPT}],
    )
    # thinking blocks may come first, so read only text blocks
    text = "".join(b.text for b in r.content if b.type == "text")
    return f"{text!r} (stop_reason={r.stop_reason})"


def nvidia():
    from openai import OpenAI

    client = OpenAI(base_url=os.environ["NVIDIA_BASE_URL"], api_key=os.environ["NVIDIA_API_KEY"])
    r = client.chat.completions.create(
        model=os.environ["NVIDIA_MODEL"],
        messages=[{"role": "user", "content": PROMPT}],
        max_tokens=20,
    )
    return repr(r.choices[0].message.content)


def openai_provider():
    from openai import OpenAI

    client = OpenAI()  # reads OPENAI_API_KEY
    r = client.responses.create(model=os.environ["OPENAI_MODEL"], input=PROMPT)
    return repr(r.output_text)


if __name__ == "__main__":
    for name, fn in [("claude", claude), ("nvidia", nvidia), ("openai", openai_provider)]:
        try:
            print(f"{name}: OK -> {fn()}")
        except Exception as e:  # report and continue with the next provider
            print(f"{name}: FAILED -> {type(e).__name__}: {e}")
