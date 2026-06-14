from __future__ import annotations

import json
from typing import Any

import httpx

from core.config_manager import ConfigManager
from core.schemas import LLMAction


class LLMClient:
    def __init__(self, config: ConfigManager) -> None:
        self.config = config

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.config.llm_api_key()}",
            "Content-Type": "application/json",
        }
        site_url = self.config.get("llm", "site_url", default="")
        site_name = self.config.get("llm", "site_name", default="")
        if site_url:
            headers["HTTP-Referer"] = site_url
        if site_name:
            headers["X-Title"] = site_name
        return headers

    def chat(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        if not self.config.llm_api_key():
            return {
                "raw": "",
                "message": "LLM API key is not configured. Add it to secrets/.env before running autonomous tasks.",
                "tools": [{"tool": "finish", "message": "LLM API key is not configured."}],
                "input_tokens": 0,
                "output_tokens": 0,
                "cached_tokens": 0,
                "total_tokens": 0,
                "cost_usd": None,
                "model": self.config.get("llm", "model"),
            }
        payload = {
            "model": self.config.get("llm", "model"),
            "messages": messages,
            "temperature": self.config.get("llm", "temperature", default=0.2),
            "max_tokens": self.config.get("llm", "max_tokens", default=4096),
        }
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self.config.get('llm', 'base_url').rstrip('/')}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        raw_message = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        parsed = self.parse_response(raw_message)
        return {
            "raw": raw_message,
            "message": parsed.message,
            "tools": [tool.model_dump() for tool in parsed.tools],
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "cached_tokens": usage.get("prompt_tokens_details", {}).get("cached_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "cost_usd": data.get("usage", {}).get("cost"),
            "model": data.get("model", self.config.get("llm", "model")),
        }

    def parse_response(self, raw_message: str) -> LLMAction:
        try:
            payload = json.loads(raw_message)
            return LLMAction.model_validate(payload)
        except Exception:
            return LLMAction(message=raw_message.strip(), tools=[{"tool": "finish", "message": raw_message.strip() or "Done"}])
