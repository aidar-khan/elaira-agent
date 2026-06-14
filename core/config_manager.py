from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


class ConfigManager:
    def __init__(self, root: Path | None = None) -> None:
        self.agent_root = root or Path(__file__).resolve().parents[1]
        load_dotenv(self.agent_root / "secrets" / ".env")
        self.config_path = self.agent_root / "config.json"
        if not self.config_path.exists():
            example_path = self.agent_root / "config.example.json"
            self.config_path.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
        self._config = json.loads(self.config_path.read_text(encoding="utf-8"))

    def get(self, *path: str, default: Any = None) -> Any:
        current: Any = self._config
        for item in path:
            if not isinstance(current, dict):
                return default
            current = current.get(item)
            if current is None:
                return default
        return current

    def require_password(self) -> str:
        env_name = self.get("auth", "password_env", default="ELAIRA_AGENT_PASSWORD")
        return os.environ.get(env_name, "")

    def llm_api_key(self) -> str:
        env_name = self.get("llm", "api_key_env", default="OPENROUTER_API_KEY")
        return os.environ.get(env_name, "")

