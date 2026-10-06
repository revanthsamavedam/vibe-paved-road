from pathlib import Path

from agent.vibe_agent import FileChange, FilePlan, apply_plan, errors_only, scaffold_app, skill_catalog

ROOT = Path(__file__).parent.parent


def test_six_pattern_skills_present_and_catalogued():
    names = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))
    assert names == ["allowlist-calls", "entra-auth", "governed-data",
                     "internal-hosting", "no-secrets", "writes-and-audit"]
    catalog = skill_catalog()
    for n in names:
        assert n in catalog


def test_apply_plan_writes_and_validates(tmp_path):
    app_dir = scaffold_app(tmp_path / "app")
    plan = FilePlan(summary="add a notes file",
                    files=[FileChange(path="notes.txt", content="hello")])
    # .txt is out of validator scope; plan applies, app still passes
    assert errors_only(apply_plan(app_dir, plan)) == []
    assert (app_dir / "notes.txt").read_text() == "hello"


def test_apply_plan_blocks_path_escape(tmp_path):
    app_dir = scaffold_app(tmp_path / "app")
    plan = FilePlan(summary="evil", files=[FileChange(path="../escape.py", content="x")])
    try:
        apply_plan(app_dir, plan)
        raise AssertionError("should have raised")
    except ValueError:
        pass
