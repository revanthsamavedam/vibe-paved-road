# The patterns — what "on-pattern" means for a vibe-coded app

Business users will vibe code either way. The choice is whether their app lands
on some offsite host with a pasted API key and no auth — or inside the firm's
patterns by default. This file is the pattern list, in the order a generated
app is checked against it. Every rule here is also (a) a skill the coding
agent loads, and (b) a check the validator enforces. One source, two enforcements.

## P1 — Hosting: internal only
- Apps deploy to the firm's internal container/app platform. Preview links are internal URLs behind SSO.
- Never: offsite PaaS (Vercel, Netlify, Railway, Heroku, Fly, Render), personal cloud accounts, `*.vercel.app`-style public URLs.
- A generated app ships a `Dockerfile` + health endpoint, not a vendor config file.

## P2 — Identity: the firm's login or nothing
- Every app sits behind Entra SSO. The backend receives the user's token (on-behalf-of) and authorizes via the internal JWT auth service — the same chain as every other internal app.
- Never: app-local passwords, "public link" sharing, API keys as user identity, auth code copied from a tutorial.
- Unauthenticated route = only `/healthz`.

## P3 — Data: through APIs, from governed sources
- Frontend never talks to a database. Ever. Frontend → your backend API → data.
- Operational/current data: Postgres (system of record), via the service's own account.
- Historical/bulk: batch data in S3 via Athena/Dremio, partition-filtered, freshness shown in the UI.
- Never: connection strings in code, a spreadsheet of client data uploaded to an external tool, direct DB access from generated JS.

## P4 — Secrets: there are none in the app
- The app holds **zero** secrets. Service credentials live in Vault / CyberArk and belong to the service tier; model/API access goes through the firm's gateway with the app's service identity.
- Never: a key pasted into code, `.env` committed, a key in frontend JS (that is public by definition).

## P5 — External calls: allowlist or blocked
- Generated code may call internal APIs and the sanctioned model gateway. Nothing else, without an approved exception recorded in the app registry.
- Never: a random SaaS API the model suggested, personal analytics/trackers, CDN-loaded libraries (vendor your assets; the app must run on the internal network).

## P6 — Writes: preview, confirm, trace
- Read-only is the default tier. An app that writes, sends, or submits needs: a user confirmation step, an approval where the pattern requires it, and an audit record of who did what, when.
- Every app emits structured logs + a trace id per request to the firm's observability stack from day one — not "add logging later".

## P7 — Lifecycle: registered or it doesn't exist
- Every vibe-coded app is registered (owner, purpose, data sources, tier) before preview. Owner leaves → app is reassigned or retired. Unregistered apps found running are treated as shadow IT, because they are.

## The deal you offer business users

You get: v0/Lovable speed, a working preview today, data wired in without a ticket queue.
You give up: choosing the host, the login system, or where the keys live.
That's the whole bargain — speed inside the patterns, no speed outside them.
