# CardOps AI Architecture

## Shape

CardOps AI is a local-first monorepo:

- `apps/api`: FastAPI application, SQLAlchemy models, Alembic migrations, provider capability detection, and REST routes.
- `apps/worker`: Durable local worker that claims database jobs and executes long-running work.
- `apps/web`: React/Vite operations UI.
- `packages/shared`: Small shared TypeScript utilities.
- `packages/schemas`: Shared TypeScript and Python schema placeholders.
- `data`: Local runtime data, demo outputs, thumbnails, exports, backups, logs, and SQLite database.
- `scripts`: Native PowerShell setup, development, test, build, demo reset, and doctor commands.

## Local-First Defaults

The API binds to `127.0.0.1`, uses SQLite by default, and runs without eBay or OpenAI credentials. Cloud AI, live eBay publishing, and physical file moves are disabled by default and exposed as settings/capabilities rather than hidden assumptions.

## Backend

The backend uses FastAPI, Pydantic v2, SQLAlchemy 2, and Alembic. The schema is SQLite-first but avoids deliberate SQLite-only data modeling where practical. API startup creates missing local tables for developer ergonomics, while `scripts/setup.ps1` and `scripts/reset-demo.ps1` use Alembic migrations.

Core tables in the current vertical slice:

- `directory_roots`
- `image_assets`
- `file_operation_manifests`
- `card_instances`
- `field_provenance`
- `jobs`
- `audit_logs`
- `settings`

Every manual card field creates a provenance row. OCR and AI providers will append evidence rows in later phases rather than overwriting user corrections.

## Worker

The local MVP uses a database-backed queue in `jobs`. The worker claims queued jobs, records attempts, writes results or redacted errors, and supports cancellation/retry state. This keeps Redis optional for the MVP while leaving queue internals replaceable.

Current job type:

- `directory_scan`

Planned job types include OCR, image preprocessing, AI vision, eBay sync, listing audit, lot optimization, and exports.

## Image Ingestion

Registered folders become allowed roots. Directory scans validate that candidate files remain inside the root unless symlink support is explicitly enabled. Ingestion never mutates originals. It stores path metadata, file times, SHA-256, perceptual hash, dimensions, EXIF orientation, thumbnail path, duplicate status, and front/back filename hints.

Image Inbox roots are normalized with a platform-safe resolved path key to reduce duplicate roots caused by slash style, case, or equivalent resolved paths. Root listing responses include availability status, indexed image count, and pending-identification count. Removing a root revokes it from CardOps only; it does not delete physical files. Users can optionally remove that root's image records from the CardOps index, and the operation is recorded in `file_operation_manifests` for auditability.

Root actions currently supported:

- Register and scan a validated local directory.
- Browse for a folder through the local Windows API process.
- Re-index a root through the existing background job system.
- Reconnect a revoked or temporarily unavailable root.
- Change a root path after validation and duplicate checks.
- Open an active root in File Explorer.
- Remove a root with confirmation and optional index-record cleanup.

## Providers

External integrations are represented as provider capability records. A missing or restricted provider reports what it can and cannot do without blocking local inventory workflows.

Current capability records:

- `MockEbayProvider`
- `EbaySandboxProvider` or `EbayProductionProvider`
- `LocalOnlyVisionProvider`
- `OpenAIVisionProvider`
- `TesseractOcrProvider`
- `MockPricingProvider`

## eBay OAuth Callback

The project uses a CardOps-specific free GitHub Pages callback when no branded production domain is configured:

```text
https://940smiley.github.io/cardops/ebay/callback/
```

This URL is the value for eBay Developer Portal Auth Accepted URL and Auth Declined URL. It is also stored in `EBAY_REDIRECT_URI` so the app can validate local configuration.

Important eBay detail: eBay authorization requests normally use the eBay-generated RuName in the OAuth `redirect_uri` parameter. CardOps therefore supports both:

- `EBAY_REDIRECT_URI`: the real HTTPS callback endpoint.
- `EBAY_RUNAME`: the eBay Redirect URL name used in the authorization URL after eBay creates it.

The GitHub Pages callback is published from a dedicated `gh-pages` branch containing only static callback files. It forwards the OAuth response to the local callback route `/ebay/callback` when CardOps is running. The local route redacts OAuth authorization codes before logging. The full code is not written to logs because it is a short-lived credential.

## Frontend

The web app is a desktop-first operations UI, not a chat interface. The current implemented sections are Dashboard, Inventory, Image Inbox, Jobs, and Settings. Planned sections remain visible as disabled navigation items until their backend workflows exist.

The UI uses React, TypeScript, Vite, TanStack Query, TanStack Table, React Hook Form, Zod, and lucide-react icons.
