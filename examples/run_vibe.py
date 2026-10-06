"""End-to-end demo without an LLM key.

Scaffolds an app from the starter, applies a deliberately off-pattern
change (an offsite config) and shows the validator catching it, then
removes it and shows the pass — the generate → check → coach loop.

    python -m examples.run_vibe
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from agent.vibe_agent import FilePlan, FileChange, apply_plan, errors_only, scaffold_app

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as td:
        app_dir = scaffold_app(Path(td) / "my-app")
        print("scaffolded from starter:", sorted(p.name for p in app_dir.iterdir()))

        bad = FilePlan(summary="user asked to deploy it publicly",
                       files=[FileChange(path="vercel.json", content="{}")])
        findings = apply_plan(app_dir, bad)
        for f in errors_only(findings):
            print(f"CAUGHT [{f.rule}] {f.message}\n  Fix: {f.fix}")

        (app_dir / "vercel.json").unlink()
        print("after fix — errors:", len(errors_only(apply_plan(app_dir, FilePlan(summary="clean")))))
