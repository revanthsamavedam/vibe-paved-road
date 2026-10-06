"""Studio chat pipeline — the real thing, not a demo brain.

Flow per message:
  1. Input screening (platform DLP, not the model): a pasted secret is
     refused before it can reach the model, the files, or the logs.
  2. The Pydantic AI vibe agent receives the message + the app's current
     file list + its pattern-skills instructions, and returns a FilePlan.
  3. apply_plan() writes the plan; the validator runs.
  4. If validation fails, the findings are fed back to the agent ONCE for
     a repair plan. If it still fails, the user sees the findings — the
     preview only ever shows the last state, and status reports the fail.
  5. Reply = agent's plan summary + what changed + validator verdict.

MODEL INTEGRATION IS THE ONLY SWAP LEFT: the agent's model comes from
the WORKPLACE_MODEL env var (see agent/vibe_agent.py). Unset = Pydantic
AI's TestModel, which exercises this whole pipeline with placeholder
output. Set it to your gateway/Azure/OpenAI model string and the same
pipeline generates real apps — no code changes in this file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from agent.vibe_agent import FilePlan, apply_plan, errors_only, scaffold_app, vibe_agent
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


def _prompt(s: Session, message: str, repair_findings: list | None = None) -> str:
    files = "\n".join(f"- {p}" for p in s.status()["files"])
    base = (
        f"User request: {message}\n\n"
        f"The app was scaffolded from the starter. Current files:\n{files}\n\n"
        "Return a FilePlan: the minimal file changes that fulfil the request "
        "while following every pattern skill. Prefer editing frontend/index.html "
        "and backend/main.py over adding files. Keep all pattern properties: "
        "internal hosting, SSO auth, data via backend API, no secrets, "
        "allowlisted calls only, confirmation+audit for writes."
    )
    if repair_findings:
        listed = "\n".join(f"- [{f.rule}] {f.file}:{f.line} {f.message} Fix: {f.fix}"
                           for f in repair_findings)
        base += (f"\n\nYour previous plan FAILED the pattern validator. "
                 f"Return a corrected FilePlan that resolves these findings "
                 f"(change or remove the offending files):\n{listed}")
    return base


async def handle_message(s: Session, message: str) -> dict:
    s.history.append({"role": "user", "text": message})

    # 1. DLP screen — secrets never reach the model.
    if any(rgx.search(message) for rgx in SECRET_RES):
        reply = ("That looks like a secret, so I stopped before it reached the "
                 "model or any file. Apps here need no pasted keys — access runs "
                 "through the firm's gateway and service accounts. Treat that "
                 "secret as exposed and rotate it. (Pattern P4)")
        s.history.append({"role": "assistant", "text": reply})
        return {"reply": reply, "changed": [], **s.status()}

    # 2–3. Agent plan → apply → validate.
    result = await vibe_agent.run(_prompt(s, message))
    plan: FilePlan = result.output
    findings = apply_plan(s.app_dir, plan)
    changed = [f.path for f in plan.files]
    errs = errors_only(findings)

    # 4. One repair round-trip with the findings as feedback.
    repaired = False
    if errs:
        result2 = await vibe_agent.run(_prompt(s, message, repair_findings=errs))
        plan2: FilePlan = result2.output
        findings = apply_plan(s.app_dir, plan2)
        changed += [f.path for f in plan2.files]
        errs = errors_only(findings)
        repaired = True

    # 5. Reply from what actually happened.
    verdict = "validator: PASS" if not errs else \
        "validator: FAIL — " + "; ".join(f"[{e.rule}] {e.message}" for e in errs)
    reply = (f"{plan.summary}\n\nChanged: {', '.join(changed) or 'no files'}"
             f"{' (after one validator repair round)' if repaired else ''} · {verdict}"
             f" · preview updated.")
    s.history.append({"role": "assistant", "text": reply})
    return {"reply": reply, "changed": changed, **s.status()}
