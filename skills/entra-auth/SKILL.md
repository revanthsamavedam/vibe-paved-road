---
name: entra-auth
description: Wire the firm's Entra SSO + internal JWT authorization into a generated app. Use when an app is created, when routes are added, and whenever a user asks for login, users, or sharing.
---

# Entra auth (Pattern P2)

- Backend middleware validates the forwarded Entra token (on-behalf-of) on every route except `/healthz`, then authorizes via the internal JWT auth service before any data access.
- The caller's identity comes only from the validated token — never from a request parameter, header the client sets freely, or a form field.
- Never generate: login pages with app-local passwords, sign-up flows, "share via public link", session secrets you invent, or hardcoded test users.
- Sharing means: the other person signs in with their firm account and their token decides what they see.
