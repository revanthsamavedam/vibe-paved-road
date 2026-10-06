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
your message goes to the Pydantic AI vibe agent → FilePlan → applied → validator
(with one automatic repair round-trip on failure) → preview + status update.

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
