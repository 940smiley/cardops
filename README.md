# CardOps AI

CardOps AI is a local-first sports and trading card operations app for inventory, image ingestion, listing review, lot planning, and eBay-safe draft workflows.

This repository uses the requested CardOps AI monorepo layout at the repository root. The physical folder is currently named `cardops`, so `DECISIONS.md` records that naming deviation.

## Current Vertical Slice

Implemented now:

- FastAPI backend with SQLite, SQLAlchemy 2, Alembic, structured health and capability endpoints.
- Durable database-backed jobs for local directory scans.
- Local image ingestion that preserves originals, calculates SHA-256 and perceptual hashes, generates thumbnails, and flags duplicate files.
- Manual inventory card creation and editing with field-level provenance.
- Demo mode with generated placeholder card images and seeded inventory.
- React/Vite frontend for Dashboard, Inventory, Image Inbox, Jobs, and Settings.
- Local deterministic OCR/filename card identification workflow with review-before-save.
- eBay-ready listing CSV, lot assignment CSV, and safe file-plan export generation.
- Double-click Windows launcher for setup, launch modes, diagnostics, configuration, provider checks, logs, and safe process management.
- Native PowerShell scripts for setup, development, tests, build, demo reset, and diagnostics.

Cloud AI, live eBay publishing, and physical file moves are disabled by default.

## Prerequisites

- Windows 10 or 11
- PowerShell 7 or Windows PowerShell 5.1
- Python 3.12+
- Node.js 20+
- `uv`
- `corepack` for installing `pnpm`

Run:

```powershell
.\scripts\doctor.ps1
```

## Setup

```powershell
.\scripts\setup.ps1
```

The setup script installs Python dependencies with `uv`, enables `pnpm` through Corepack when needed, installs frontend dependencies, and applies database migrations. It does not delete user data.

## Run

Double-click:

```text
CardOps-Launcher.cmd
```

or from PowerShell:

```powershell
.\CardOps-Launcher.cmd
```

The launcher is the primary control center for live, demo, and local-only modes. It tracks CardOps PIDs, checks ports, captures logs under `logs/launcher`, edits local configuration with secrets redacted, and can generate a diagnostic report.

Script-only development remains available:

```powershell
.\scripts\dev.ps1
```

Default local URLs:

- API: http://127.0.0.1:8000
- OpenAPI: http://127.0.0.1:8000/docs
- Web: http://127.0.0.1:5173

## Test

```powershell
.\scripts\test.ps1
```

For browser workflow tests, install Playwright browsers during setup or run:

```powershell
corepack pnpm --filter @cardops/web exec playwright install chromium
.\scripts\test.ps1 -IncludeE2E
```

## Demo Data

Reset local demo data:

```powershell
.\scripts\reset-demo.ps1
```

Preview what would change:

```powershell
.\scripts\reset-demo.ps1 -DryRun
```

Demo mode uses generated placeholder images stored under `data/demo/images`. These are not marketplace photos.

## Card Workflow

Current end-to-end local workflow:

1. Register a local image folder in Image Inbox.
2. Use the Image Inbox root controls to browse, validate, reconnect, re-index, open, change, or remove configured roots.
3. Scan the folder to ingest supported images and detect duplicates by file hash.
4. Open Identification Review.
5. Analyze an image with local Tesseract OCR when configured, or deterministic filename fallback when OCR is unavailable.
6. Review confidence, evidence, and unresolved fields.
7. Correct fields manually before saving a card.
8. Export inventory, eBay-ready listing CSV, lot assignment CSV, or safe file-plan CSV.

CardOps does not silently invent uncertain card information. Low-confidence or missing fields stay visible for review.

Removing an Image Inbox root removes it from CardOps configuration only. Physical directories and image files remain on disk. The removal dialog shows the root path, indexed image count, pending identification count, and an optional index-record cleanup choice before confirmation.

## Privacy And Safety Defaults

- API binds to `127.0.0.1`.
- Images remain local.
- Cloud AI is opt-in and disabled.
- eBay publishing is disabled.
- Physical file moves are disabled.
- OAuth tokens and API keys must be configured locally and must never be committed.
- Original images are never modified by ingestion.

## Environment

Copy `.env.example` to `.env` and adjust as needed. The app runs without credentials.

Key values:

- `CARDOPS_DATABASE_URL`
- `CARDOPS_DEMO_MODE`
- `OPENAI_API_KEY`
- `OPENAI_MODEL_FAST`
- `OPENAI_MODEL_ACCURATE`
- `EBAY_ENVIRONMENT`
- `EBAY_CLIENT_ID`
- `EBAY_CLIENT_SECRET`
- `EBAY_REDIRECT_URI`
- `EBAY_RUNAME`
- `CARDOPS_TESSERACT_CMD`
- `CARDOPS_OCR_LANGUAGE`
- `CARDOPS_CONFIDENCE_THRESHOLD`

## OCR And Tesseract

Tesseract is optional. Without it, CardOps still ingests images and uses filename-based identification hints. For OCR, install Tesseract and either put `tesseract.exe` on `PATH` or set:

```text
CARDOPS_TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
CARDOPS_OCR_LANGUAGE=eng
```

The launcher includes Tesseract detection, locate, documentation, and install actions. Install actions show the package source and require confirmation.

## eBay OAuth Callback

This project uses a free CardOps-specific GitHub Pages callback for eBay OAuth callbacks:

```text
https://940smiley.github.io/cardops/ebay/callback/
```

Paste that same URL into eBay Developer Portal:

- Auth Accepted URL
- Auth Declined URL

Then set:

```text
EBAY_REDIRECT_URI=https://940smiley.github.io/cardops/ebay/callback/
```

After eBay generates a Redirect URL name / RuName, put that value in `EBAY_RUNAME`. eBay authorization URLs use the RuName, while `EBAY_REDIRECT_URI` remains the real HTTPS callback URL.

Diagnostics and repair:

```powershell
node .\scripts\oauth_debug.js
.\scripts\fix.ps1
```

The scripts use `data/tmp` on the developer drive for temporary test files so a full Windows system drive does not break normal project validation.

The public callback is published from a dedicated `gh-pages` branch containing only static callback files.

## Limitations

This repository currently supports local inventory, image ingestion, deterministic OCR/filename identification review, CSV exports, and safe eBay OAuth URL generation. Full eBay token exchange, encrypted token storage, seller sync, AI vision, live publishing, and reversible physical file sorting remain planned in `TASKS.md`.

More launcher detail is in `docs/LAUNCHER.md`.
