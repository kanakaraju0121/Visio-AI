#!/usr/bin/env python3
"""Optional terminal chat client for the configured Groq account."""

import os


def main() -> int:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        print("Set GROQ_API_KEY in your environment before running this tool.")
        return 2
    try:
        from groq import Groq
    except ImportError:
        print("Install the optional dependency with: pip install groq")
        return 2

    client = Groq(api_key=api_key)
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    print("Visio-AI terminal assistant (type 'exit' to quit)")
    while True:
        try:
            prompt = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return 0
        if prompt.lower() in {"exit", "quit"}:
            print("Goodbye.")
            return 0
        if not prompt:
            continue
        try:
            result = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
            )
            print("AI:", result.choices[0].message.content or "(empty response)")
        except Exception as exc:
            print(f"Request failed: {type(exc).__name__}")


if __name__ == "__main__":
    raise SystemExit(main())
