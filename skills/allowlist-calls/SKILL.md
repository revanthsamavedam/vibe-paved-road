---
name: allowlist-calls
description: Restrict generated code's outbound calls to internal APIs and the sanctioned model gateway. Use when an app needs to call any API or load any library.
---

# Allowlist calls (Pattern P5)

- Allowed without discussion: the app's own backend, internal APIs on the firm's domains, the sanctioned model gateway.
- Libraries: vendor the asset into the repo or use the internal package mirror — no CDN `<script>`/`<link>` tags, no runtime fetches from public CDNs. The app must work with no internet access.
- Anything else is an exception: stop, name the external service and what data would leave, and tell the user it needs an approved exception in the app registry before it can be added.
- Never add analytics, trackers, error-reporting SaaS, or "free tier" APIs the model happens to know about.
