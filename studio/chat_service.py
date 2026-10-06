"""Studio chat pipeline — subagents behind an orchestrator.

Flow per message:
  1. Input screening (platform DLP, not a model): a pasted secret is
     refused before it can reach any agent, the files, or the logs.
  2. The ORCHESTRATOR (agent/orchestrator.py) runs the builder (frontend)
     and data (backend) subagents in parallel, filters their FilePlans
     to scope, and merges them.
  3. The REVIEWER subagent gates the merged plan before anything is
     written — a veto triggers one revision round, then nothing applies.
  4. An approved plan is applied; the deterministic validator runs, with
     one repair round routed to the owning-scope subagent on errors.
  5. Reply = pipeline summary + agents used + reviewer verdict + what
     changed + validator verdict. The response also carries agents_used
     and reviewer as structured fields for the UI status bar.

MODEL INTEGRATION IS THE ONLY SWAP LEFT: every subagent's model comes
from the WORKPLACE_MODEL env var (see agent/subagents.py). Unset =
Pydantic AI's TestModel, which exercises this whole pipeline with
placeholder output (its generated reviewer verdict defaults to a veto —
the safe direction). Set it to your gateway/Azure/OpenAI model string
and the same pipeline generates real apps, no code changes here.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from agent.orchestrator import run_pipeline
from agent.vibe_agent import errors_only, scaffold_app
from validator.vibe_check import SECRET_RES, check_project


@dataclass
class Session:
    id: str
    user: str
    app_dir: Path
    history: list[dict] = field(default_factory=list)

    def status(self) -> dict:
        findings = check_project(self.app_dir)
        files = sorted(str(p.relative_to(self.app_dir))
                       for p in self.app_dir.rglob("*") if p.is_file())
        return {"session_id": self.id,
                "model": os.environ.get("WORKPLACE_MODEL", "test"),
                "validator": "pass" if not errors_only(findings) else "fail",
                "findings": [f.__dict__ for f in findings],
                "files": files,
                "preview_url": f"/preview/{self.id}/"}


def new_session(sessions: dict, session_id: str, user: str, base_dir: Path) -> Session:
    app_dir = scaffold_app(base_dir / session_id)
    s = Session(id=session_id, user=user, app_dir=app_dir)
    sessions[session_id] = s
    return s


async def handle_message(s: Session, message: str) -> dict:
    s.history.append({"role": "user", "text": message})

    # 1. DLP screen — secrets never reach a model.
    if any(rgx.search(message) for rgx in SECRET_RES):
        reply = ("That looks like a secret, so I stopped before it reached the "
                 "model or any file. Apps here need no pasted keys — access runs "
                 "through the firm's gateway and service accounts. Treat that "
                 "secret as exposed and rotate it. (Pattern P4)")
        s.history.append({"role": "assistant", "text": reply})
        return {"reply": reply, "changed": [], "agents_used": [],
                "reviewer": None, **s.status()}

    # 2–4. Orchestrated subagents: delegate -> reviewer gate -> apply -> validate.
    result = await run_pipeline(s.app_dir, message)

    rev = result.reviewer
    reviewer_txt = ("reviewer: APPROVED" if rev["approved"] else
                    "reviewer: VETOED — " + ("; ".join(rev["issues"]) or rev["summary"]
                                             or "no specifics given"))
    agents_txt = " → ".join(result.agents_used)
    verdict = f"validator: {result.validator.upper()}"
    dropped_txt = (f" · dropped out-of-scope: {', '.join(result.dropped)}"
                   if result.dropped else "")
    if result.applied:
        tail = f"Changed: {', '.join(result.changed) or 'no files'} · preview updated."
    else:
        tail = "Nothing was applied (reviewer veto) — the preview is unchanged."
    reply = (f"{result.summary}\n\nAgents: {agents_txt} · {reviewer_txt} · "
             f"{verdict}{dropped_txt}\n{tail}")
    s.history.append({"role": "assistant", "text": reply})
    return {"reply": reply, "changed": result.changed,
            "agents_used": result.agents_used, "reviewer": result.reviewer,
            **s.status()}
