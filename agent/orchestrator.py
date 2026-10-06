"""Orchestrator — coordinates the subagents, owns the gates.

Pipeline per user message:
  1. builder + data subagents run IN PARALLEL, each asked for a FilePlan
     in its own scope.
  2. Each plan is FILTERED to its scope in code (out-of-scope files are
     dropped and reported, never applied).
  3. Merged plan goes to the reviewer subagent BEFORE anything is
     written. Veto -> one revision round (issues fed back to both
     subagents) -> reviewer again -> still vetoed = NOTHING is applied.
  4. Approved plan is applied; the deterministic validator runs.
     Validation errors trigger ONE repair round, routed only to the
     subagent(s) owning the offending files' scope, reviewer-gated
     like any other plan before it is applied.

The orchestrator itself is code, not an LLM: delegation order, scope
filtering, and the two gates (reviewer, validator) are too important to
leave to a model's discretion. The intelligence lives in the subagents;
the discipline lives here.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from agent.subagents import (
    BUILDER_PREFIXES,
    DATA_PREFIXES,
    builder_agent,
    data_agent,
    reviewer_agent,
)
from agent.vibe_agent import FilePlan, apply_plan, errors_only
from validator.vibe_check import Finding, check_project


@dataclass
class PipelineResult:
    summary: str
    changed: list[str]
    agents_used: list[str]
    reviewer: dict  # {approved, issues, summary}
    validator: str  # "pass" | "fail"
    findings: list[Finding]
    applied: bool = False
    dropped: list[str] = field(default_factory=list)


def filter_plan(plan: FilePlan, prefixes: tuple[str, ...]) -> tuple[FilePlan, list[str]]:
    """Keep only files inside the scope prefixes. Returns (kept, dropped_paths)."""
    kept = [f for f in plan.files if f.path.startswith(prefixes)]
    dropped = [f.path for f in plan.files if not f.path.startswith(prefixes)]
    return FilePlan(summary=plan.summary, files=kept), dropped


def owner_scope_for_file(path: str) -> str:
    if path.startswith(BUILDER_PREFIXES):
        return "builder"
    if path.startswith(DATA_PREFIXES):
        return "data"
    return "both"


def _file_list(app_dir: Path) -> list[str]:
    return sorted(str(p.relative_to(app_dir)) for p in app_dir.rglob("*") if p.is_file())


def _subagent_prompt(scope: str, message: str, files: list[str], extra: str = "") -> str:
    listing = "\n".join(f"- {f}" for f in files)
    return (
        f"User request: {message}\n\n"
        f"You own the {scope} scope only. The app was scaffolded from the "
        f"starter. Current files:\n{listing}\n\n"
        "Return a FilePlan with the minimal changes in YOUR scope that "
        "your part of this request needs. If your scope needs no changes, "
        "return an empty files list. Follow every pattern skill in your "
        f"instructions.{extra}"
    )


def _review_prompt(plan: FilePlan, files: list[str]) -> str:
    listing = "\n".join(f"- {f}" for f in files)
    return (
        "Review this proposed FilePlan for a vibe-coded internal app.\n\n"
        f"App's current files:\n{listing}\n\n"
        f"Proposed plan (JSON):\n{plan.model_dump_json(indent=2)}\n\n"
        "Return your ReviewVerdict."
    )


async def _delegate(message: str, files: list[str],
                    extra: str = "") -> tuple[FilePlan, list[str]]:
    """Run builder + data in parallel; return (merged scoped plan, dropped)."""
    b_res, d_res = await asyncio.gather(
        builder_agent.run(_subagent_prompt("frontend", message, files, extra)),
        data_agent.run(_subagent_prompt("backend", message, files, extra)),
    )
    b_plan, b_dropped = filter_plan(b_res.output, BUILDER_PREFIXES)
    d_plan, d_dropped = filter_plan(d_res.output, DATA_PREFIXES)
    merged = FilePlan(
        summary=f"builder: {b_plan.summary} · data: {d_plan.summary}",
        files=b_plan.files + d_plan.files,
    )
    return merged, b_dropped + d_dropped


async def _review(plan: FilePlan, files: list[str]):
    return (await reviewer_agent.run(_review_prompt(plan, files))).output


async def _repair(app_dir: Path, message: str, errs: list[Finding]) -> list[str]:
    """One repair round, routed to owning-scope subagents, reviewer-gated.

    Returns the list of files the repair changed (empty if the repair was
    vetoed or produced nothing).
    """
    owners = {owner_scope_for_file(e.file) for e in errs}
    listed = "\n".join(f"- [{e.rule}] {e.file}:{e.line} {e.message} Fix: {e.fix}"
                       for e in errs)
    extra = (f"\n\nThe applied app FAILED the pattern validator with these "
             f"findings. Return a FilePlan in your scope that fixes the "
             f"ones in your scope:\n{listed}")
    files_now = _file_list(app_dir)

    jobs, scopes = [], []
    if owners & {"builder", "both"}:
        jobs.append(builder_agent.run(_subagent_prompt("frontend", message, files_now, extra)))
        scopes.append(BUILDER_PREFIXES)
    if owners & {"data", "both"}:
        jobs.append(data_agent.run(_subagent_prompt("backend", message, files_now, extra)))
        scopes.append(DATA_PREFIXES)

    repair_files = []
    for res, prefixes in zip(await asyncio.gather(*jobs), scopes):
        kept, _dropped = filter_plan(res.output, prefixes)
        repair_files += kept.files
    if not repair_files:
        return []

    repair_plan = FilePlan(summary="validator repair", files=repair_files)
    verdict = await _review(repair_plan, files_now)
    if not verdict.approved:
        return []  # a vetoed repair is not applied; the fail stands and is reported
    apply_plan(app_dir, repair_plan)
    return [f.path for f in repair_files]


async def run_pipeline(app_dir: str | Path, message: str) -> PipelineResult:
    app_dir = Path(app_dir)
    agents_used: list[str] = []

    def note(name: str) -> None:
        if name not in agents_used:
            agents_used.append(name)

    files = _file_list(app_dir)
    merged, dropped = await _delegate(message, files)
    note("builder"); note("data")

    verdict = await _review(merged, files)
    note("reviewer")

    if not verdict.approved:  # one revision round with the issues as feedback
        issues = "\n".join(f"- {i}" for i in verdict.issues) or "- (no specifics given)"
        extra = (f"\n\nThe reviewer VETOED the previous attempt with these "
                 f"issues. Produce a corrected plan that resolves them:\n{issues}")
        merged, dropped2 = await _delegate(message, files, extra)
        dropped += dropped2
        verdict = await _review(merged, files)

    reviewer_dict = {"approved": verdict.approved,
                     "issues": list(verdict.issues),
                     "summary": verdict.summary}

    if not verdict.approved:  # still vetoed -> apply nothing
        findings = check_project(app_dir)
        return PipelineResult(
            summary=merged.summary, changed=[], agents_used=agents_used,
            reviewer=reviewer_dict,
            validator="pass" if not errors_only(findings) else "fail",
            findings=findings, applied=False, dropped=dropped)

    findings = apply_plan(app_dir, merged)
    changed = [f.path for f in merged.files]

    if errors_only(findings):  # one repair round through the owning subagents
        changed += await _repair(app_dir, message, errors_only(findings))
        findings = check_project(app_dir)

    return PipelineResult(
        summary=merged.summary, changed=changed, agents_used=agents_used,
        reviewer=reviewer_dict,
        validator="pass" if not errors_only(findings) else "fail",
        findings=findings, applied=True, dropped=dropped)
