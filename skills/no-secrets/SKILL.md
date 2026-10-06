---
name: no-secrets
description: Enforce zero secrets in generated code. Use on every generation, and whenever a user pastes a key, token, password, or connection string.
---

# No secrets (Pattern P4)

- Generated code contains no API keys, tokens, passwords, or connection strings. Config arrives via environment at deploy time; real service credentials live in Vault / CyberArk and never reach the app, the user, or you.
- Model/API access goes through the firm's gateway using the app's service identity — generate a gateway client call, not a key.
- If a user pastes a secret: do not use it, do not repeat it back, do not put it in a file. Tell them it isn't needed here and that a pasted secret should be treated as exposed and rotated.
- `.env.example` lists names only, with empty values.
