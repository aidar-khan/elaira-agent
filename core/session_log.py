from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


class SessionLog:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.session_path = root / "sessions" / "active.jsonl"
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.session_path.exists():
            self.append_event({"type": "session_started", "time": now_iso()})

    def append_event(self, event: dict[str, Any]) -> None:
        line = json.dumps(event, ensure_ascii=False)
        with self.session_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def read_events(self) -> list[dict[str, Any]]:
        if not self.session_path.exists():
            return []
        events: list[dict[str, Any]] = []
        with self.session_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    events.append({"type": "corrupt_line", "raw": line, "time": now_iso()})
        return events

    def archive_and_reset(self) -> Path | None:
        events = self.read_events()
        if not events:
            return None
        timestamp = datetime.now().astimezone()
        archive_dir = self.root / "history" / timestamp.strftime("%Y/%m/%d")
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / f"session_{timestamp.strftime('%H%M%S')}.jsonl"
        archive_path.write_text(self.session_path.read_text(encoding="utf-8"), encoding="utf-8")
        self.session_path.write_text("", encoding="utf-8")
        self.append_event({"type": "session_started", "time": now_iso()})
        return archive_path

