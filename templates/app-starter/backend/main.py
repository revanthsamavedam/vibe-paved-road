"""App starter backend — every pattern pre-applied.

P1 internal hosting (Dockerfile alongside) · P2 Entra token validated on
every route except /healthz, authorized via the internal JWT auth service
(stub below — swap `validate_token` for the real call) · P3 data only via
this API, using the service's own account in the service tier · P4 zero
secrets in code · P6 writes need confirmation + write an audit record,
every request gets a trace id and a structured log line.
"""
from __future__ import annotations

import json
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI(title="vibe-app")


def validate_token(authorization: str | None) -> str:
    """Stub for the real chain: Entra OBO token -> internal JWT auth service.

    Returns the caller id. Production replaces the body only.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "sign-in required")
    token = authorization.removeprefix("Bearer ").strip()
    if token.startswith("demo:"):  # local preview only — remove with the stub
        return token.split(":")[1]
    raise HTTPException(401, "unrecognised token (production validates via the auth service)")


@app.middleware("http")
async def trace_and_auth(request: Request, call_next):
    trace_id = uuid.uuid4().hex[:16]
    start = time.time()
    if request.url.path not in ("/healthz", "/"):
        try:
            caller = validate_token(request.headers.get("Authorization"))
        except HTTPException as e:
            # Middleware runs outside FastAPI's exception handlers —
            # an HTTPException raised here would surface as a 500.
            return JSONResponse(status_code=e.status_code,
                                content={"detail": e.detail})
        request.state.caller = caller
    response = await call_next(request)
    print(json.dumps({"trace_id": trace_id, "path": request.url.path,
                      "status": response.status_code,
                      "ms": round((time.time() - start) * 1000)}))
    response.headers["x-trace-id"] = trace_id
    return response


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse("../frontend/index.html")


_ITEMS = [{"id": 1, "title": "Example item", "status": "open"}]


@app.get("/api/items")
def list_items(request: Request):
    # Service tier would read Postgres here with its OWN governed account,
    # authorised for request.state.caller — never with the caller's creds.
    return {"caller": request.state.caller, "items": _ITEMS,
            "freshness": "live (system of record)"}


class NewItem(BaseModel):
    title: str
    confirm: bool = False  # P6: a write must be explicitly confirmed


@app.post("/api/items")
def create_item(item: NewItem, request: Request):
    if not item.confirm:
        raise HTTPException(409, "preview first, then re-send with confirm=true")
    record = {"id": len(_ITEMS) + 1, "title": item.title, "status": "open"}
    print(json.dumps({"audit": "item.created", "caller": request.state.caller,
                      "item_id": record["id"]}))  # P6 audit record
    _ITEMS.append(record)
    return record
