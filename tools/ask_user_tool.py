from __future__ import annotations


def ask_user(question: str) -> dict[str, str]:
    return {"type": "ask_user", "question": question}

