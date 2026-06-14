from __future__ import annotations

import json
import re
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
            payload = self._extract_payload(raw_message)
            return self._normalize_action(payload, raw_message)
        except Exception:
            return LLMAction(message=raw_message.strip(), tools=[{"tool": "finish", "message": raw_message.strip() or "Done"}])

    def _extract_payload(self, raw_message: str) -> dict[str, Any]:
        try:
            payload = json.loads(raw_message)
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass

        objects = self._extract_json_objects(raw_message)
        leading_text = raw_message.split("{", 1)[0].strip() if "{" in raw_message else raw_message.strip()
        tool_objects = [item for item in objects if isinstance(item, dict) and (item.get("tool") or item.get("name"))]
        action_objects = [item for item in objects if isinstance(item, dict) and ("message" in item or "tools" in item)]

        if action_objects:
            payload = dict(action_objects[-1])
            payload_tools = payload.get("tools", [])
            if isinstance(payload_tools, list):
                payload["tools"] = [*tool_objects, *payload_tools]
            elif tool_objects:
                payload["tools"] = tool_objects
            if leading_text and not payload.get("message"):
                payload["message"] = leading_text
            return payload

        if tool_objects:
            return {"message": leading_text or "Proceeding with the requested action.", "tools": tool_objects}

        return {"message": raw_message.strip(), "tools": []}

    def _normalize_action(self, payload: dict[str, Any], raw_message: str) -> LLMAction:
        normalized = dict(payload)
        tools = normalized.get("tools", [])

        if isinstance(tools, dict):
            tools = [tools]

        normalized_tools: list[dict[str, Any]] = []
        for tool in tools:
            if isinstance(tool, str):
                normalized_tools.append({"tool": tool})
                continue
            if isinstance(tool, dict):
                normalized_tool = dict(tool)
                tool_name = normalized_tool.get("tool") or normalized_tool.get("name")
                if tool_name:
                    normalized_tool["tool"] = tool_name
                if tool_name == "bash" and not normalized_tool.get("command"):
                    normalized_tool["command"] = normalized_tool.get("input")
                if tool_name == "ask_user" and not normalized_tool.get("question"):
                    normalized_tool["question"] = normalized_tool.get("input") or normalized.get("message")
                if tool_name == "notify_user" and not normalized_tool.get("message"):
                    normalized_tool["message"] = normalized_tool.get("input") or normalized.get("message")
                if tool_name == "finish" and not normalized_tool.get("message"):
                    normalized_tool["message"] = normalized_tool.get("input") or normalized.get("message")
                if tool_name == "bash" and not normalized_tool.get("command"):
                    continue
                if tool_name == "ask_user" and not normalized_tool.get("question"):
                    continue
                normalized_tools.append(normalized_tool)

        normalized["tools"] = normalized_tools
        normalized["message"] = str(normalized.get("message", raw_message.strip() or "Done"))
        action = LLMAction.model_validate(normalized)

        # If the model asked a question but omitted the normalized tool block, convert it explicitly.
        if not action.tools and normalized_tools:
            return LLMAction(message=action.message, tools=normalized_tools)  # type: ignore[arg-type]

        return action

    def _extract_json_objects(self, raw_message: str) -> list[Any]:
        decoder = json.JSONDecoder()
        objects: list[Any] = []
        index = 0
        while index < len(raw_message):
            match = re.search(r"[\{\[]", raw_message[index:])
            if not match:
                break
            start = index + match.start()
            try:
                parsed, end = decoder.raw_decode(raw_message[start:])
                objects.append(parsed)
                index = start + end
            except Exception:
                index = start + 1
        return objects
