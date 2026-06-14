from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router as api_router
from api.websocket import WebsocketHub
from core.agent_loop import AgentLoop
from core.config_manager import ConfigManager
from core.memory_loader import ensure_memory_files
from core.recovery import summarize_session_state
from core.session_log import SessionLog


def create_app() -> FastAPI:
    config = ConfigManager()
    ensure_memory_files(config.agent_root)
    session_log = SessionLog(config.agent_root)
    ws_hub = WebsocketHub()
    agent_loop = AgentLoop(config=config, session_log=session_log, ws_hub=ws_hub)

    app = FastAPI(title="Elaira Agent", version="0.1.0")
    app.state.config = config
    app.state.session_log = session_log
    app.state.ws_hub = ws_hub
    app.state.agent_loop = agent_loop

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(config.agent_root / "ui" / "index.html")

    @app.on_event("startup")
    async def startup() -> None:
        summary = summarize_session_state(session_log.read_events())
        await ws_hub.broadcast({"type": "status", "state": summary["session_state"]})

    app.include_router(api_router)
    app.mount("/ui", StaticFiles(directory=config.agent_root / "ui"), name="ui")
    return app


app = create_app()

