import asyncio
from pathlib import Path

from pydantic_ai.models.test import TestModel

from agent.orchestrator import filter_plan, owner_scope_for_file, run_pipeline
from agent.subagents import (
    builder_agent,
    data_agent,
    reviewer_agent,
    skill_body,
    ReviewVerdict,
)
from agent.vibe_agent import FileChange, FilePlan, scaffold_app

ROOT = Path(__file__).parent.parent

APPROVING = TestModel(custom_output_args={
    "approved": True, "issues": [], "summary": "on-pattern"})


def test_subagents_exist_with_scoped_skills():
    assert builder_agent is not data_agent is not reviewer_agent
    # scoped skill bodies actually loaded
    assert "Governed data" in skill_body("governed-data")
    assert "Entra auth" in skill_body("entra-auth")
    assert "No secrets" in skill_body("no-secrets")


def test_filter_plan_drops_out_of_scope_files():
    plan = FilePlan(summary="mixed", files=[
        FileChange(path="frontend/index.html", content="<html></html>"),
        FileChange(path="backend/main.py", content="x"),
        FileChange(path="vercel.json", content="{}"),
    ])
    kept, dropped = filter_plan(plan, ("frontend/",))
    assert [f.path for f in kept.files] == ["frontend/index.html"]
    assert dropped == ["backend/main.py", "vercel.json"]


def test_owner_scope_routing():
    assert owner_scope_for_file("frontend/index.html") == "builder"
    assert owner_scope_for_file("backend/main.py") == "data"
    assert owner_scope_for_file("Dockerfile") == "both"


async def _run_reviewer():
    return await reviewer_agent.run("Review this plan: no files changed.")


def test_reviewer_output_is_verdict():
    result = asyncio.run(_run_reviewer())
    assert isinstance(result.output, ReviewVerdict)
    assert isinstance(result.output.approved, bool)
    # TestModel's generated verdict defaults to a veto — the safe direction.
    assert result.output.approved is False


def test_orchestrator_veto_applies_nothing(tmp_path):
    app_dir = scaffold_app(tmp_path / "app")
    before = (app_dir / "frontend" / "index.html").read_text()
    result = asyncio.run(run_pipeline(app_dir, "Add a team updates heading"))
    assert result.agents_used == ["builder", "data", "reviewer"]
    assert result.reviewer["approved"] is False  # TestModel reviewer vetoes
    assert result.applied is False and result.changed == []
    assert (app_dir / "frontend" / "index.html").read_text() == before
    assert result.validator == "pass"  # untouched starter still validates


def test_orchestrator_approval_applies_only_in_scope(tmp_path):
    app_dir = scaffold_app(tmp_path / "app")
    new_frontend = ("<!doctype html><html><head><title>Orchestrated</title>"
                    "</head><body><h1>Orchestrated</h1></body></html>")
    builder_override = TestModel(custom_output_args={
        "summary": "update the page",
        "files": [
            {"path": "frontend/index.html", "content": new_frontend},
            {"path": "backend/evil.py", "content": "print('out of scope')"},
        ]})
    with builder_agent.override(model=builder_override), \
            reviewer_agent.override(model=APPROVING):
        result = asyncio.run(run_pipeline(app_dir, "Rename the page"))
    assert result.reviewer["approved"] is True
    assert result.applied is True
    assert result.changed == ["frontend/index.html"]
    assert result.dropped == ["backend/evil.py"]
    assert not (app_dir / "backend" / "evil.py").exists()
    assert "Orchestrated" in (app_dir / "frontend" / "index.html").read_text()
    assert result.validator == "pass"
