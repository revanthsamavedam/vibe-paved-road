# vibe-paved-road

Vibe coding for business users — **on the firm's patterns, not on some offsite host.**
Sanitized template: generic pattern names in code, no employer data, demo auth stub only.

Start with **[PATTERNS.md](PATTERNS.md)** (the pattern list, P1–P7) and
**[PLAYBOOK.md](PLAYBOOK.md)** (a 1-pager for business users + rollout notes for the builder).

## The idea

Business users will vibe code either way. So give them the speed where it's safe:
- **Start from the road** — every app begins as `templates/app-starter/` (FastAPI + plain frontend, Dockerfile, auth middleware, trace ids, audit-on-write pre-applied). Never a blank repo, never a vendor template.
- **Patterns as skills** — `skills/` holds 6 SKILL.md files (internal hosting, Entra auth, governed data, no secrets, allowlist calls, writes & audit) that the coding agent must follow. Patterns are prompts *and* policy, versioned in git.
- **A fence, not a lecture** — `validator/vibe_check.py` scans every generated app against the patterns: offsite deploy configs, hardcoded secrets, non-allowlisted external calls, connection strings, frontend-to-DB, missing auth. Findings coach with the on-pattern fix; nothing previews until it passes.
- **The agent loop** — `agent/vibe_agent.py` (Pydantic AI): prompt → structured FilePlan → apply → validate → coach → re-check.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
python -m validator.vibe_check templates/app-starter   # should PASS, 0 errors
python -m examples.run_vibe                             # generate → check → coach demo
```

Pairs with the **workplace-muse** template: apps generated here consume data
through the same MCP connectors and the same identity chain (user token →
internal JWT auth service → service's own governed account).

## Going real

1. Recreate internally per the workplace SETUP intake guidance — don't import personal code into the firm blind.
2. Point the starter's `validate_token` at the real auth chain, the gateway URL at the sanctioned model gateway, and the platform deploy at your internal app platform.
3. Extend `ALLOWED_HOSTS` in the validator to your real internal domains. Keep the list short — that's the point.
