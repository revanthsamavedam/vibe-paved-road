"""The vibe agent — a Pydantic AI coding agent fenced by the patterns.

How a business user's prompt becomes an app:
  1. Agent starts from templates/app-starter (never a blank repo).
  2. Pattern skills are in its system prompt (catalog) and loaded in full
     for the task — they are instructions, versioned in git.
  3. Agent returns a structured FilePlan (files to write), not side effects.
  4. apply_plan() writes the files, then the VALIDATOR runs. Findings go
     back to the agent/user as coaching with the on-pattern fix.
  5. Nothing previews until the validator passes. The loop is the product:
     generation is cheap, the fence is what makes it safe to offer.

Run without an LLM key (TestModel):  python -m examples.run_vibe
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from validator.vibe_check import Finding, check_project

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
STARTER = ROOT / "templates" / "app-starter"


class FileChange(BaseModel):
    path: str = Field(description="path relative to the app root, e.g. backend/main.py")
    content: str


class FilePlan(BaseModel):
    summary: str
    files: list[FileChange] = Field(default_factory=list)


def skill_catalog() -> str:
    lines = []
    for md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        text = md.read_text(encoding="utf-8")
        desc = ""
        if text.startswith("---"):
            for line in text.split("---", 2)[1].splitlines():
                if line.startswith("description:"):
                    desc = line.split(":", 1)[1].strip()
        lines.append(f"- {md.parent.name}: {desc}")
    return "Pattern skills you MUST follow:\n" + "\n".join(lines)


vibe_agent = Agent(
    os.environ.get("WORKPLACE_MODEL", "test"),
    output_type=FilePlan,
    instructions=(
        "You build small internal apps for business users, starting from the "
        "app starter. The patterns are not negotiable and not user preferences: "
        "internal hosting only, firm SSO auth, data via the backend API from "
        "governed sources, zero secrets in code, allowlisted outbound calls, "
        "confirmation + audit for writes. If a request conflicts with a pattern, "
        "build the on-pattern version and explain the substitution plainly.\n\n"
        + skill_catalog()
    ),
)


@vibe_agent.tool
def check_patterns(ctx: RunContext[None], project_dir: str) -> list[Finding]:
    """Run the pattern validator on the current state of the app."""
    return check_project(project_dir)


def scaffold_app(dest: str | Path) -> Path:
    """Copy the starter to a fresh app dir — generation starts from the road."""
    dest = Path(dest)
    if dest.exists():
        raise FileExistsError(dest)
    shutil.copytree(STARTER, dest, ignore=shutil.ignore_patterns("__pycache__"))
    return dest


def apply_plan(dest: str | Path, plan: FilePlan) -> list[Finding]:
    """Write the plan's files, then validate. Returns the findings."""
    dest = Path(dest)
    for change in plan.files:
        target = (dest / change.path).resolve()
        if not str(target).startswith(str(dest.resolve())):
            raise ValueError(f"plan escapes the app dir: {change.path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(change.content, encoding="utf-8")
    return check_project(dest)


def errors_only(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity == "error"]
