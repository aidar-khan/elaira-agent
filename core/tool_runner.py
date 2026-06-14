from __future__ import annotations

from pathlib import Path
from typing import Any

from api.websocket import WebsocketHub
from core.config_manager import ConfigManager
from core.session_log import SessionLog, now_iso
from tools.ask_user_tool import ask_user
from tools.bash_tool import run_bash
from tools.finish_tool import finish
from tools.notify_user_tool import notify_user


class ToolRunner:
    def __init__(self, config: ConfigManager, session_log: SessionLog, ws_hub: WebsocketHub) -> None:
        self.config = config
        self.session_log = session_log
        self.ws_hub = ws_hub

    async def run_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for tool in tools:
            tool_name = tool.get("tool")
            if tool_name == "notify_user":
                event = {"time": now_iso(), **notify_user(tool.get("message", ""))}
                self.session_log.append_event(event)
                await self.ws_hub.broadcast(event)
                results.append(event)
            elif tool_name == "ask_user":
                event = {"time": now_iso(), **ask_user(tool.get("question", ""))}
                self.session_log.append_event(event)
                await self.ws_hub.broadcast(event)
                results.append(event)
                break
            elif tool_name == "finish":
                event = {"time": now_iso(), **finish(tool.get("message", ""))}
                self.session_log.append_event(event)
                await self.ws_hub.broadcast(event)
                results.append(event)
                break
            elif tool_name == "bash":
                started = {"type": "tool_started", "time": now_iso(), "tool": "bash", "command": tool.get("command", "")}
                self.session_log.append_event(started)
                await self.ws_hub.broadcast(started)
                configured_directory = Path(
                    self.config.get("bash", "working_directory", default=str(self.config.agent_root))
                )
                working_directory = configured_directory if configured_directory.exists() else self.config.agent_root
                event = run_bash(
                    command=tool.get("command", ""),
                    working_directory=str(working_directory),
                    timeout_seconds=int(self.config.get("bash", "timeout_seconds", default=120)),
                )
                event["time"] = now_iso()
                self.session_log.append_event(event)
                await self.ws_hub.broadcast(event)
                results.append(event)
            else:
                event = {"type": "error", "time": now_iso(), "message": f"Unknown tool: {tool_name}"}
                self.session_log.append_event(event)
                await self.ws_hub.broadcast(event)
                results.append(event)
        return results
