"""Optional Groq-backed conversational responses for Visio-AI."""

from __future__ import annotations

import os
from typing import Optional

try:
    from groq import Groq
except ImportError:  # The robot can still run without the optional cloud AI feature.
    Groq = None  # type: ignore[assignment,misc]

_client = None


def is_ai_available() -> bool:
    """Return whether the Groq client can be initialized from environment config."""
    global _client
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or Groq is None:
        return False
    if _client is None:
        try:
            _client = Groq(api_key=api_key)
        except Exception:
            _client = None
            return False
    return True


def _limit_sentences(text: str, maximum: int = 2) -> str:
    """Keep spoken responses concise without failing on empty API responses."""
    text = (text or "").strip()
    if not text:
        return "I could not generate a response."
    sentence_count = 0
    for index, character in enumerate(text):
        if character in ".!?":
            sentence_count += 1
            if sentence_count >= maximum:
                return text[: index + 1].strip()
    return text


def get_ai_response(user_input: str) -> str:
    """Generate a short response using Groq; return a safe message if unavailable."""
    global _client
    if not is_ai_available():
        return "AI is unavailable. Configure GROQ_API_KEY to enable it."

    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()
    try:
        response = _client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful robot assistant. Reply in no more than two short sentences.",
                },
                {"role": "user", "content": user_input},
            ],
            max_tokens=100,
        )
        content: Optional[str] = response.choices[0].message.content
        return _limit_sentences(content or "")
    except Exception as exc:
        # Do not print request contents or credentials to logs.
        print(f"Groq request failed: {type(exc).__name__}")
        return "Sorry, I could not reach the AI service."
