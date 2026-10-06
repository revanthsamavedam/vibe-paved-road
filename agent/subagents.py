"""Subagents — like Muse's, each is a narrower agent, not a prompt trick.

Three Pydantic AI agents, all on the SAME model (WORKPLACE_MODEL env var,
default "test" = TestModel). What differs is scope + instructions:

  builder_agent   frontend only   -> may only return files under frontend/
  data_agent      backend only    -> may only return files under backend/
  reviewer_agent  builds NOTHING  -> returns a ReviewVerdict and can veto

Each agent's instructions embed the bodies of the pattern skills relevant
to its scope (skills/*/SKILL.md) — the same skills, versioned in git, that
the single vibe agent used as a catalog. Scope is ALSO enforced in code
by the orchestrator (agent/orchestrator.py filters every FilePlan to its
scope): instructions say "stay in your lane", the filter makes it true
even when a model doesn't.
"""
from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from agent.vibe_agent import SKILLS_DIR, FilePlan

ROOT = Path(__file__).resolve().parent.parent

BUILDER_PREFIXES = ("frontend/",)
DATA_PREFIXES = ("backend/",)


def skill_body(name: str) -> str:
    """Full text of one pattern skill, frontmatter stripped."""
    text = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
    if text.startswith("---"):
        return text.split("---", 2)[-1].strip()
    return text.strip()


def _skills(*names: str) -> str:
    return "\n\n".join(skill_body(n) for n in names)


_MODEL = os.environ.get("WORKPLACE_MODEL", "test")

builder_agent = Agent(
    _MODEL,
    output_type=FilePlan,
    instructions=(
        "You are the BUILDER subagent of a vibe-coding studio. You own the "
        "frontend only: every file you return MUST be under frontend/. "
        "You never touch backend code, data access, hosting config, or "
        "anything with credentials. Build the on-pattern version of what "
        "was asked and say plainly in the summary if you substituted "
        "anything for pattern reasons.\n\n"
        + _skills("internal-hosting", "writes-and-audit", "allowlist-calls")
    ),
)

data_agent = Agent(
    _MODEL,
    output_type=FilePlan,
    instructions=(
        "You are the DATA subagent of a vibe-coding studio. You own the "
        "backend only: every file you return MUST be under backend/. "
        "Data reaches the app only through this backend API, from governed "
        "sources, using the service's own account. You never touch "
        "frontend files, and you never put a connection string, key, or "
        "secret in any file.\n\n"
        + _skills("governed-data", "entra-auth", "no-secrets", "allowlist-calls")
    ),
)


class ReviewVerdict(BaseModel):
    approved: bool
    issues: list[str] = Field(default_factory=list)
    summary: str = ""


_PATTERNS = (ROOT / "PATTERNS.md").read_text(encoding="utf-8")

reviewer_agent = Agent(
    _MODEL,
    output_type=ReviewVerdict,
    instructions=(
        "You are the REVIEWER subagent of a vibe-coding studio. You build "
        "nothing and change nothing — you judge a proposed FilePlan "
        "against the firm's patterns and return a ReviewVerdict. "
        "Veto (approved=false, issues naming the exact file and pattern) "
        "if the plan: deploys or references offsite hosting; contains or "
        "introduces any secret, key, or connection string; lets the "
        "frontend reach a database or an external host directly; drops "
        "or weakens SSO/token auth; adds a write/send/delete without "
        "confirmation + audit; or touches files outside the app. "
        "Approve an empty / no-change plan (issues=[]). When in doubt "
        "about a pattern, veto — a human can override you, the pipeline "
        "cannot.\n\nPATTERNS:\n" + _PATTERNS
        + "\n\nSKILLS:\n" + _skills(
            "internal-hosting", "entra-auth", "governed-data",
            "no-secrets", "allowlist-calls", "writes-and-audit")
    ),
)
