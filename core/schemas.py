from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class UserMessageRequest(BaseModel):
    text: str = Field(min_length=1)


class FileWriteRequest(BaseModel):
    path: str
    content: str


class ToolCall(BaseModel):
    tool: str
    command: str | None = None
    message: str | None = None
    question: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        tool_name = normalized.get("tool") or normalized.get("name")
        normalized["tool"] = tool_name
        input_value = normalized.get("input")

        if tool_name == "bash" and input_value and not normalized.get("command"):
            normalized["command"] = input_value
        elif tool_name == "ask_user" and input_value and not normalized.get("question"):
            normalized["question"] = input_value
        elif tool_name in {"notify_user", "finish"} and input_value and not normalized.get("message"):
            normalized["message"] = input_value

        return normalized


class LLMAction(BaseModel):
    message: str
    tools: list[ToolCall] = Field(default_factory=list)
