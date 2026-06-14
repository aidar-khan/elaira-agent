from __future__ import annotations

import json
from typing import Any

from api.websocket import WebsocketHub
from core.config_manager import ConfigManager
from core.git_manager import GitManager
from core.llm_client import LLMClient
from core.memory_loader import load_memory_context
from core.session_log import SessionLog, now_iso
from core.tool_runner import ToolRunner


class AgentLoop:
    def __init__(self, config: ConfigManager, session_log: SessionLog, ws_hub: WebsocketHub) -> None:
        self.config = config
        self.session_log = session_log
        self.ws_hub = ws_hub
        self.llm_client = LLMClient(config)
        self.tool_runner = ToolRunner(config, session_log, ws_hub)
        self.git_manager = GitManager(config.agent_root)

    def _build_messages(self, user_text: str, tool_results: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
        memory = load_memory_context(self.config.agent_root)
        system_prompt = memory.get("system_prompt.md", "")
        events = self.session_log.read_events()[-40:]
        transcript = "\n".join(json.dumps(event, ensure_ascii=False) for event in events)
        tools_text = json.dumps(tool_results or [], ensure_ascii=False)
        return [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": "Memory:\n" + "\n\n".join(f"[{name}]\n{content}" for name, content in memory.items() if name != "system_prompt.md")},
            {"role": "system", "content": f"Recent session log:\n{transcript}"},
            {"role": "user", "content": user_text},
            {"role": "system", "content": f"Latest tool results:\n{tools_text}"},
        ]

    async def run_task(self, user_text: str) -> dict[str, Any]:
        last_tools: list[dict[str, Any]] = []
        final_event: dict[str, Any] = {"type": "finish", "message": "No work done"}
        max_cycles = int(self.config.get("agent", "max_cycles_per_task", default=20))
        for cycle in range(max_cycles):
            messages = self._build_messages(user_text=user_text, tool_results=last_tools)
            self.session_log.append_event(
                {
                    "type": "llm_request",
                    "time": now_iso(),
                    "model": self.config.get("llm", "model"),
                    "messages_count": len(messages),
                    "cycle": cycle + 1,
                }
            )
            response = self.llm_client.chat(messages)
            llm_event = {
                "type": "llm_response",
                "time": now_iso(),
                **response,
            }
            self.session_log.append_event(llm_event)
            await self.ws_hub.broadcast(llm_event)

            tools = response.get("tools", [])
            if not tools:
                tools = [{"tool": "finish", "message": response.get("message", "Done")}]

            last_tools = await self.tool_runner.run_tools(tools)
            if not last_tools:
                final_event = {"type": "finish", "message": response.get("message", "Done")}
                self.session_log.append_event({"time": now_iso(), **final_event})
                await self.ws_hub.broadcast({"time": now_iso(), **final_event})
                break

            final_event = last_tools[-1]
            if final_event.get("type") in {"ask_user", "finish"}:
                break

        if final_event.get("type") == "finish" and self.config.get("agent", "auto_git_commit", default=True):
            git_result = self.git_manager.auto_commit_after_turn(final_event.get("message", "completed"))
            git_event = {"type": "git_commit", "time": now_iso(), **git_result}
            self.session_log.append_event(git_event)
            await self.ws_hub.broadcast(git_event)
            if self.config.get("agent", "auto_git_push", default=False):
                push_result = self.git_manager.git_push()
                push_event = {"type": "git_push", "time": now_iso(), **push_result}
                self.session_log.append_event(push_event)
                await self.ws_hub.broadcast(push_event)

        return final_event

