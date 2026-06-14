from __future__ import annotations


def finish(message: str) -> dict[str, str]:
    return {"type": "finish", "message": message}

