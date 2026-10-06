# Playbook

## For business users (the 1-pager you hand them)

1. **Describe it** in the internal vibe studio — what it shows, who uses it, what data it needs. Plain English is fine.
2. **Get a preview** on an internal link. Share it only inside the firm, via SSO.
3. **Ask for data** by naming the dataset, not by uploading files. If the data exists in the firm's sources, it gets wired in; if it doesn't, that's a data request, not a workaround.
4. **Iterate by describing changes.** Don't ask the AI to "use this API key" or "host it here" — hosting, login, and keys are already handled and are not options.
5. **Register before you rely on it.** Owner, purpose, audience. Two minutes. Unregistered apps can be retired without notice.
6. **Know your tier.** Read-only dashboards: fast lane. Anything that writes, sends, or submits: confirmation + approval step gets added — the studio will tell you, you don't decide it away.

Red lines the studio will simply refuse: external hosting, your own login system, pasted keys, connecting a personal account, uploading client data to an outside tool. Refusal isn't bureaucracy — it's the app protecting you from owning a breach.

## For the builder (rolling this out at work)

1. **Don't launch a platform. Launch a template + a checker.** Week 1–2: the starter (`templates/app-starter/`), the validator (`validator/`) wired as a required CI/preview gate, and 3 pattern skills (auth, data, secrets). That's a shippable thing a platform team can nod at.
2. **Recruit one business team with a real itch** — a dashboard they currently maintain in spreadsheets. Build their first app *with* them in the studio. Their demo sells the next five teams.
3. **Make the paved road faster than the offsite road.** Preview in minutes, data via existing MCP connectors (see workplace-muse), no tickets for read-only tier. If going offsite is easier, people will — speed is the governance strategy.
4. **Registry from day one**, even if it's a table: app, owner, tier, data sources, last check result. This is your answer when risk/compliance asks "what's running?" — and they will.
5. **Validator findings are coaching, not punishment.** Every failure message names the pattern, why it exists, and the on-pattern alternative the agent can apply automatically. Most fixes should be one click / one re-prompt.
6. **Tier the freedom.** Read-only internal: near-total freedom. Writes: + confirmation/approval pattern. External data or clients: out of vibe scope — that's a real project with real engineering.
