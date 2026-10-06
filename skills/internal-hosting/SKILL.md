---
name: internal-hosting
description: Generate the deployment shape for an internal app — Dockerfile, health endpoint, internal preview. Use for every new app and every deploy-related request.
---

# Internal hosting (Pattern P1)

- Produce a `Dockerfile` for the firm's internal container platform and a `/healthz` endpoint that needs no auth.
- App must read its port and config from environment, bind `0.0.0.0`, and run fully on the internal network (no external downloads at build or run time — vendor all assets).
- Never generate: `vercel.json`, `netlify.toml`, Procfile-for-Heroku, deploy instructions for any offsite PaaS, or a public URL. If the user asks to "put it on Vercel", refuse that part and offer the internal preview instead.
- Preview = an internal URL behind SSO. Phrase it that way in user-facing text.
