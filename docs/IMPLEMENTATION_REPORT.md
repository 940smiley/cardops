# CardOps Implementation Report

## Completed

- Added planned-updates phase 1 for Image Inbox root management and filesystem safety foundations.
- Added normalized root path keys to prevent equivalent duplicate inbox roots.
- Added root status detection for active, revoked, missing, invalid, unavailable, and moved roots.
- Added root image counts and pending-identification counts to directory responses.
- Added safe root removal with explicit confirmation, optional CardOps index cleanup, physical-file retention, and operation manifest logging.
- Added local folder browse, reconnect, change-path, re-index, and open-in-Explorer actions.
- Added `file_operation_manifests` as a reusable audit structure for later rename, move, copy, and undo workflows.
- Added a unified Windows launcher with live, demo, local-only, frontend-only, API-only, and full-stack launch actions.
- Added tracked process management, port checks, structured launcher logs, log rotation, and redacted diagnostic report generation.
- Added configuration editing and redacted import/export behavior for local `.ENV`.
- Added dependency checks for Python, uv, Node.js, Corepack, Git, and Tesseract.
- Added local Tesseract OCR detection/execution and deterministic filename fallback.
- Added local card field normalization with confidence, unresolved fields, and extraction evidence.
- Added image identification and create-from-image API endpoints.
- Added Identification Review UI for analyze, edit, and save.
- Added eBay title length validation, listing recommendation, lot assignment, listing CSV export, lot CSV export, and safe file-plan export.

## Planned Updates Resolved

- Phase 2 OCR: partially completed. Tesseract detection/execution, fallback analysis, review UI, and provenance are implemented. OpenCV preprocessing, bounding boxes, and word-level OCR confidence remain deferred.
- Phase 3 AI Vision: deferred. Cloud AI remains opt-in and disabled; no image data is sent online by default.
- Phase 4 eBay Read Integration: partially completed. OAuth URL/callback diagnostics are working. Token exchange, encrypted token storage, seller sync, and business policy retrieval remain deferred.
- Phase 5 Listing Audit: partially completed. Title validation and CSV listing records are implemented. Full listing scoring, item specifics validation, descriptions, and diffs remain deferred.
- Phase 6 Lot Builder: partially completed. Deterministic lot assignment and CSV export are implemented. Competing strategies and lock workflow remain deferred.
- Phase 7 Drafts/Publishing: deferred. Live publishing remains disabled and requires explicit future implementation.
- Phase 8 Physical Sorting: partially completed. Non-destructive file-plan export is implemented. Copy/move/rollback workflows remain deferred.
- Phase 9 Launcher: completed except installer packaging and GUI automation tests.

## Planned Updates Phase 1 Change Report

Files changed:

- `apps/api/cardops_api/models.py`
- `apps/api/cardops_api/filesystem_service.py`
- `apps/api/cardops_api/image_service.py`
- `apps/api/cardops_api/routes.py`
- `apps/api/cardops_api/schemas.py`
- `apps/web/src/api.ts`
- `apps/web/src/components/ImageInbox.tsx`
- `apps/web/src/styles.css`
- `apps/web/src/types.ts`
- `tests/api/test_directory_scan.py`
- `docs/ARCHITECTURE.md`
- `docs/IMPLEMENTATION_REPORT.md`

New migration:

- `apps/api/alembic/versions/0004_root_management_and_file_manifests.py`

New settings:

- None in this phase. The requested settings for filename templates, collision policy, preserve-original image behavior, sort hierarchy, pricing, audit thresholds, job concurrency, retry limits, and backups remain scheduled for later phases.

Tests added:

- Duplicate root prevention using normalized paths.
- Root count and pending-identification reporting.
- Confirmed root removal without deleting physical image files.
- Optional root index-record cleanup.
- Missing-directory status detection.

Remaining limitations:

- The Browse action is implemented for Windows local API runs. Browser security prevents a normal web page from reading arbitrary full folder paths without local helper support.
- Image editing, filename templates, bulk rename, physical sorting, Pricing, Lot Builder, Listings, Listing Audits, and expanded Jobs remain planned.
- File operation manifests are now available, but move/copy/rename undo workflows are not implemented in this phase.

## Security Review

- Secrets stay in ignored local env files and are not written to source-controlled files.
- Launcher logs and diagnostic reports redact API keys, tokens, passwords, and known secret formats.
- Demo mode uses local/mock providers and an isolated demo database.
- Local-only mode disables online provider calls.
- The launcher does not modify `D:\KnowledgeBase`.
- Destructive process actions require confirmation and only target tracked CardOps process trees.
