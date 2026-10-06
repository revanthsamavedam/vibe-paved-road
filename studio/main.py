"""Vibe Studio server — browser chat + live preview + pattern status.

Run:  uvicorn studio.main:app --port 8090   →  open http://localhost:8090

Auth here is the demo stub (Bearer demo:<user>) standing in for the real
chain — platform SSO (Entra) in front, the forwarded token validated per
request. In production this service sits behind that SSO like every
internal app (Pattern P2); the generated apps carry their own auth.

Model: set WORKPLACE_MODEL to your Pydantic AI model string (gateway /
Azure / OpenAI). That env var is the entire model integration.
Sessions' apps live under STUDIO_APPS_DIR (default: system temp) — in
production, one workspace per app in the registry, not a temp dir.
"""
from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from studio.chat_service import Session, handle_message, new_session

BASE_DIR = Path(os.environ.get(
    "STUDIO_APPS_DIR", Path(tempfile.gettempdir()) / "vibe-studio-apps"))
BASE_DIR.mkdir(parents=True, exist_ok=True)
STATIC = Path(__file__).parent / "static"
SESSIONS: dict[str, Session] = {}

app = FastAPI(title="vibe-studio")

OPEN_EXACT = ("/", "/healthz", "/favicon.ico")
OPEN_PREFIXES = ("/preview/",)  # iframe can't send auth headers; SSO guards it in prod


def _caller(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer demo:"):
        return auth.removeprefix("Bearer demo:").split(":")[0]
    raise HTTPException(401, "sign-in required")


@app.middleware("http")
async def auth_mw(request: Request, call_next):
    path = request.url.path
    if path in OPEN_EXACT or path.startswith(OPEN_PREFIXES):
        return await call_next(request)
    try:
        request.state.caller = _caller(request)
    except HTTPException as e:
        # Middleware sits outside FastAPI's exception handlers; returning
        # the response here is what keeps this a 401 instead of a 500.
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    return await call_next(request)


@app.get("/healthz")
def healthz():
    return {"ok": True, "model": os.environ.get("WORKPLACE_MODEL", "test")}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


class SessionIn(BaseModel):
    user: str = "alice"


@app.post("/api/session")
def create_session(body: SessionIn, request: Request):
    sid = uuid.uuid4().hex[:12]
    s = new_session(SESSIONS, sid, body.user or request.state.caller, BASE_DIR)
    return s.status()


class ChatIn(BaseModel):
    session_id: str
    message: str


@app.post("/api/chat")
async def chat(body: ChatIn):
    s = SESSIONS.get(body.session_id)
    if s is None:
        raise HTTPException(404, "unknown session — create one first")
    return await handle_message(s, body.message)


@app.get("/api/status/{session_id}")
def status(session_id: str):
    s = SESSIONS.get(session_id)
    if s is None:
        raise HTTPException(404, "unknown session")
    return s.status()


@app.get("/preview/{session_id}/")
def preview(session_id: str):
    s = SESSIONS.get(session_id)
    if s is None:
        raise HTTPException(404, "unknown session")
    page = s.app_dir / "frontend" / "index.html"
    if not page.exists():
        raise HTTPException(404, "app has no frontend page yet")
    return FileResponse(page)


# The generated app's preview page calls its own backend at /api/items.
# The studio serves the same sample shape so the preview works end-to-end;
# a generated app's real backend replaces this when it is deployed.
@app.get("/api/items")
def items(request: Request):
    return {"caller": request.state.caller,
            "items": [{"id": 1, "title": "Example item", "status": "open"}],
            "freshness": "live (system of record)"}
