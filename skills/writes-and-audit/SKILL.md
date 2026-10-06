---
name: writes-and-audit
description: Add the confirmation, approval, logging, and audit pattern to a generated app. Use whenever an app writes, sends, submits, or deletes — and for request logging in every app.
---

# Writes and audit (Pattern P6)

- Every app: structured request logs with a trace id, shipped to the firm's observability stack. Generate this in the starter middleware, not per-route.
- Any action that writes, sends, submits, or deletes gets, in order: a preview of exactly what will happen → an explicit user confirmation → where the tier requires it, an approval step → an audit record (who, what, when, trace id) written before the result is shown.
- Deletes are soft by default (mark, don't destroy) unless the user explicitly designs otherwise with the pattern owner.
- Never generate a write endpoint that acts on a bare GET, acts without the caller's validated identity, or skips the audit record "for now".
