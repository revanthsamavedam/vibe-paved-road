# App starter

The paved road in code form. A generated app starts here, never from a blank file.

- `backend/main.py` — FastAPI with the patterns pre-applied (auth middleware stub, trace ids, audit on writes, confirmation before writes)
- `frontend/index.html` — calls only the backend API, no external assets
- `Dockerfile` — the internal-platform deploy unit; `/healthz` for the platform's checks
- `.env.example` — config names only

Local preview: `pip install -r backend/requirements.txt && uvicorn backend.main:app --port 8080`, then open the internal preview URL. Local demo token: `demo:alice` (stub only, removed when the real auth chain is wired).

Before any deploy, the project must pass: `python -m validator.vibe_check .`
