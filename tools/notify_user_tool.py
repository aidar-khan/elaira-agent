from __future__ import annotations


def notify_user(message: str) -> dict[str, str]:
    return {"type": "notify_user", "message": message}

