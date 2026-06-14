from __future__ import annotations

from typing import Any


def summarize_session_state(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {"session_state": "IDLE", "last_event": {}}
    last_event = events[-1]
    event_type = last_event.get("type")
    if event_type == "ask_user":
        state = "WAITING_USER"
    elif event_type == "finish":
        state = "FINISHED"
    elif event_type in {"llm_request", "tool_started"}:
        state = "RUNNING"
    elif event_type == "error":
        state = "ERROR"
    else:
        state = "IDLE"
    return {"session_state": state, "last_event": last_event}

