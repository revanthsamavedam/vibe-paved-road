# Vibe Studio (browser UI prototype)

Split-screen: **chat on the left** (describe, iterate, get coached on patterns),
**live preview on the right**, status bar with the validator verdict and the
active model, files/findings collapsed underneath for support.

## Run it end-to-end

```bash
pip install -e ".[dev]"
uvicorn studio.main:app --port 8090
# open http://localhost:8090
```

The full pipeline runs with no model key: session → scaffold from the starter →
your message is handled by **subagents under an orchestrator**
(`agent/subagents.py`, `agent/orchestrator.py`):

1. **builder** (frontend scope only) and **data** (backend scope only)
   subagents each return a FilePlan, in parallel; the orchestrator filters
   every plan to its scope in code — out-of-scope files are dropped, never
   applied, and reported in the chat reply.
2. A **reviewer** subagent — which builds nothing — judges the merged plan
   against the patterns and can **veto** it before a single file is written.
   A veto gets one revision round; a second veto means nothing is applied.
3. Approved plans are applied, then the deterministic validator runs; any
   errors get one repair round routed to the subagent that owns the
   offending file's scope, reviewer-gated before applying.
4. Preview + status update: the status bar shows the agents used and the
   reviewer's verdict alongside the validator result.

Note on the placeholder model: TestModel's generated reviewer verdict
defaults to a veto, so with no model configured most chat turns will show
"reviewer: VETOED" and apply nothing. That's the safe direction for a
placeholder — configure a real model (below) to see approvals, or look at
`tests/test_subagents.py`, which overrides the reviewer to exercise the
approval path end-to-end.

## The one integration left: the model

The agent's model is read from **one env var** — this is the entire model
integration, by design:

```bash
WORKPLACE_MODEL="azure:gpt-4o-mini" uvicorn studio.main:app --port 8090
# or your gateway's Pydantic AI model string + its standard env credentials
```

Unset, it runs on Pydantic AI's TestModel: the pipeline, validator, repair
loop, and preview are all real; the generated content is placeholder.
Everything else — auth chain (demo stub here, SSO in front in production),
workspaces (`STUDIO_APPS_DIR`), the preview's sample `/api/items` — follows
the same swap-one-piece pattern as the MCP servers in workplace-muse.
