---
name: env
description: Use when the user needs to configure, inspect, or troubleshoot PATs, API keys, tokens, credentials, or environment variables without exposing secret values.
---

# Environment secrets

Help configure environment variables and credentials while keeping secret material out of chat, logs, source control, command output, and diffs.

## Workflow

1. Identify the target tool, variable name, scope, and required persistence. Ask only for information that cannot be discovered safely.
2. Check whether the variable or credential exists without printing its value. Prefer a tool's authenticated status command when it masks credentials.
3. Recommend the narrowest suitable store: an OS keyring or tool credential store first, a gitignored project environment file second, and a shell profile only for intentionally global configuration.
4. Before editing, ensure secret-bearing files are excluded from version control. Place names and placeholders only in example files.
5. Verify authentication or variable presence using redacted output. Report the variable name, storage location, and verification result, never the value.

## Secret-handling rules

- Never ask the user to paste a live secret into chat.
- Never print, echo, interpolate, inspect, transform, hash, or partially reveal a secret value.
- Do not put a secret directly in a command argument because it may enter shell history or process listings.
- Do not read broad environment dumps or credential files when a presence check is sufficient.
- Do not commit, upload, or include secrets in generated artifacts.
- Treat values encountered accidentally as sensitive. Stop displaying output, avoid repeating the value, and recommend revocation if exposure occurred.

Writing to shell profiles, system settings, CI secrets, cloud secret stores, or other persistent external configuration requires the user's authorization for that target. If secure input or an appropriate credential store is unavailable, provide a safe command template with a placeholder and let the user enter the value locally.
