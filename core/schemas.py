from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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


class LLMAction(BaseModel):
    message: str
    tools: list[ToolCall] = Field(default_factory=list)

