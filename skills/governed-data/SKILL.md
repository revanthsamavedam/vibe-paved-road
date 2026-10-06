---
name: governed-data
description: Connect a generated app to governed data — Postgres for current records, S3 batch via Athena/Dremio for history — always through the backend API. Use whenever an app needs data.
---

# Governed data (Pattern P3)

- Frontend calls only the app's own backend API. The API calls the data tier. No exceptions, no "just this once directly from the browser".
- Current/operational records → Postgres, using the service's own account, parameters bound (never string-built SQL).
- History/bulk → batch zone, partition-filtered queries only; the UI displays data freshness ("as of <date>") wherever batch numbers appear.
- Prefer calling the existing MCP connectors / internal APIs over generating new data-access code. If a dataset isn't available through them, say so and stop — do not invent a CSV upload workaround for firm data.
- Never generate database connection code in frontend files, and never put a connection string anywhere in generated code.
