from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, WebSocket

from core.recovery import summarize_session_state
from core.schemas import FileWriteRequest, UserMessageRequest
from core.session_log import now_iso

router = APIRouter(prefix="/api")


def _require_password(request: Request, x_agent_password: str | None = Header(default=None)) -> None:
    expected = request.app.state.config.require_password()
    if expected and x_agent_password != expected:
        raise HTTPException(status_code=401, detail="Invalid agent password")


def _guard_path(root: Path, relative_path: str) -> Path:
    path = (root / relative_path).resolve()
    blocked_roots = {root / "secrets", root / "tmp", root / ".git"}
    if not str(path).startswith(str(root.resolve())):
        raise HTTPException(status_code=400, detail="Path escapes repository root")
    for blocked in blocked_roots:
        if str(path).startswith(str(blocked.resolve())):
            raise HTTPException(status_code=403, detail="Path is not accessible")
    return path


@router.get("/status", dependencies=[Depends(_require_password)])
async def status(request: Request) -> dict[str, Any]:
    events = request.app.state.session_log.read_events()
    summary = summarize_session_state(events)
    return {"ok": True, "agent_root": str(request.app.state.config.agent_root), **summary}


@router.get("/session", dependencies=[Depends(_require_password)])
async def session(request: Request) -> dict[str, Any]:
    return {"events": request.app.state.session_log.read_events()}


@router.post("/message", dependencies=[Depends(_require_password)])
async def message(request: Request, payload: UserMessageRequest) -> dict[str, Any]:
    event = {"type": "user_message", "time": now_iso(), "text": payload.text}
    request.app.state.session_log.append_event(event)
    await request.app.state.ws_hub.broadcast(event)
    result = await request.app.state.agent_loop.run_task(payload.text)
    summary = summarize_session_state(request.app.state.session_log.read_events())
    return {"ok": True, "result": result, **summary}


@router.post("/new-session", dependencies=[Depends(_require_password)])
async def new_session(request: Request) -> dict[str, Any]:
    archive_path = request.app.state.session_log.archive_and_reset()
    return {"ok": True, "archived_to": str(archive_path) if archive_path else None}


@router.get("/files", dependencies=[Depends(_require_password)])
async def files(request: Request) -> dict[str, Any]:
    root = request.app.state.config.agent_root
    excluded = {"secrets", "tmp", ".git", ".venv", "__pycache__"}
    items = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in excluded for part in relative.parts):
            continue
        items.append({"path": str(relative), "is_dir": path.is_dir()})
    return {"items": items}


@router.get("/file", dependencies=[Depends(_require_password)])
async def read_file(request: Request, path: str = Query(...)) -> dict[str, Any]:
    file_path = _guard_path(request.app.state.config.agent_root, path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if file_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is a directory")
    return {"path": path, "content": file_path.read_text(encoding="utf-8")}


@router.post("/file", dependencies=[Depends(_require_password)])
async def write_file(request: Request, payload: FileWriteRequest) -> dict[str, Any]:
    file_path = _guard_path(request.app.state.config.agent_root, payload.path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(payload.content, encoding="utf-8")
    event = {"type": "file_write", "time": now_iso(), "path": payload.path}
    request.app.state.session_log.append_event(event)
    await request.app.state.ws_hub.broadcast(event)
    return {"ok": True, "path": payload.path}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    app = websocket.app
    expected = app.state.config.require_password()
    if expected and websocket.query_params.get("password") != expected:
        await websocket.close(code=4401)
        return
    await app.state.ws_hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        app.state.ws_hub.disconnect(websocket)

