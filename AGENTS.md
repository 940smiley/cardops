# AGENTS.md

## Project Rules

- Preserve the local-first default. The app must remain useful without eBay credentials or OpenAI credentials.
- Do not add scraping for eBay or sold-comparable data.
- Do not expose secrets in source code, logs, browser storage, screenshots, exports, or fixtures.
- Destructive file operations must stay disabled by default and require explicit user confirmation.
- Original card photographs must never be modified during ingestion.
- Prefer provider interfaces for external systems. Restricted providers should report limited capability instead of blocking unrelated workflows.
- Use migrations for schema changes.
- Keep `TASKS.md`, `DECISIONS.md`, and `CHANGELOG.md` current when implementing phases.

## Commands

- Setup: `.\scripts\setup.ps1`
- Dev: `.\scripts\dev.ps1`
- Tests: `.\scripts\test.ps1`
- Build: `.\scripts\build.ps1`
- Demo reset: `.\scripts\reset-demo.ps1`
- Diagnostics: `.\scripts\doctor.ps1`

## Safety Checks

- API must bind to `127.0.0.1` by default.
- Cloud AI defaults to off.
- Live eBay publishing defaults to off.
- Physical file moves default to off.
- Logs must redact API keys, OAuth tokens, and authorization headers.
