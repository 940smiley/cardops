# Changelog

## 0.1.0 - Phase 0 and Phase 1 vertical slice

- Added monorepo foundation with FastAPI backend, React/Vite frontend, worker, shared packages, scripts, tests, and documentation.
- Added SQLite database models, Alembic migration framework, health endpoint, settings endpoint, and capability endpoint.
- Added local directory registration, scan jobs, image hashing, thumbnail generation, duplicate detection, and revocable allowed roots.
- Added manual inventory card records with stable internal SKUs and field-level provenance.
- Added generated demo fixtures and reset workflow.
- Added dashboard, inventory table/form, image inbox, jobs, and settings UI.
- Added backend pytest coverage, frontend Vitest coverage, and Playwright workflow test harness.

## Unreleased - eBay OAuth callback repair

- Replaced the billing-required callback with a free CardOps-specific GitHub Pages callback.
- Added backend eBay OAuth callback handling and authorization URL builder.
- Added `oauth_debug.js`, `fix.ps1`, and `fix.bat` for idempotent redirect repair and GitHub Pages checks.
- Updated environment templates and documentation with Auth Accepted URL, Auth Declined URL, `EBAY_REDIRECT_URI`, and `EBAY_RUNAME`.
- Updated test script to use workspace temp storage when the Windows system drive is full.

## Unreleased - Launcher and local workflow completion

- Added `CardOps-Launcher.cmd` and `tools/CardOps-Launcher.ps1` as the Windows control center.
- Added local dependency diagnostics, Tesseract detection, OCR/filename card identification, review-before-save API, and frontend review UI.
- Added eBay-safe title recommendations, deterministic lot assignment, listing CSV export, lot CSV export, and safe file-plan export.
- Added launcher logs, redacted diagnostic report generation, safe process tracking, and mode-specific launch actions.
- Added backend tests for card normalization, title length validation, exports, and launcher self-test.
