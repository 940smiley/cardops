# CardOps AI Implementation Checklist

## Phase 0: Repository Foundation

- [x] Inspect existing repository.
- [x] Create `AGENTS.md`.
- [x] Create monorepo layout.
- [x] Create architecture documentation.
- [x] Configure backend formatting/lint/test dependencies.
- [x] Configure frontend Vite/React/TypeScript/test dependencies.
- [x] Add setup, development, test, build, demo reset, and doctor PowerShell scripts.
- [x] Add `.env.example`.
- [x] Add SQLAlchemy models and Alembic migration framework.
- [x] Add health and capability endpoints.

## Phase 1: Local Inventory MVP

- [x] Register local directories.
- [x] Persist allowed roots and support revocation.
- [x] Enqueue directory scan jobs.
- [x] Implement worker-side image ingestion.
- [x] Calculate SHA-256 hashes.
- [x] Calculate perceptual hashes.
- [x] Generate thumbnails without modifying originals.
- [x] Detect duplicate files.
- [x] Create inventory card records.
- [x] Store field-level provenance for manual card edits.
- [x] Add demo fixtures with generated placeholder images.
- [x] Add dashboard, inventory, image inbox, jobs, and settings UI.
- [x] Add backend tests for health, cards, directories, jobs, and ingestion.
- [x] Add frontend unit tests.
- [x] Add Playwright workflow test harness.

## Phase 2: OCR And Review Workflow

- [ ] Add OpenCV validation and preprocessing stages.
- [x] Add Tesseract OCR provider detection and execution.
- [ ] Store OCR bounding boxes and word-level confidence.
- [x] Implement front/back classification from filename patterns.
- [ ] Implement pairing recommendations and user approval workflow.
- [x] Build identification review UI for analyze, evidence review, correction, and save.
- [x] Preserve deterministic extraction evidence and manual corrections with provenance.

## Phase 3: AI Vision Integration

- [ ] Add OpenAI Responses API provider behind opt-in feature flag.
- [ ] Add structured output schema validation.
- [ ] Add AI response cache by image hash and prompt/schema version.
- [ ] Add batch cost estimation and daily request limits.
- [ ] Route low-confidence results to review.

## Phase 4: eBay Read Integration

- [x] Add production-safe callback endpoint and OAuth URL builder.
- [x] Add free GitHub Pages callback package.
- [x] Add OAuth redirect debug and fix scripts.
- [ ] Implement full OAuth authorization-code token exchange for Sandbox and Production.
- [ ] Encrypt stored OAuth credentials at rest.
- [ ] Add refresh-token handling and disconnect/revoke workflow.
- [ ] Implement import by URL or item number through supported eBay APIs.
- [ ] Store listing snapshots and field provenance.
- [ ] Add seller active-listing sync and business-policy retrieval.

## Phase 5: Listing Audit

- [ ] Score listing quality across required components.
- [x] Generate eBay-safe title recommendations with 80-character validation.
- [ ] Validate item specifics.
- [ ] Generate concise listing descriptions with uncertainty disclosure.
- [ ] Show before/after diffs with evidence and confidence.
- [x] Generate local eBay-ready listing CSV records without publishing.

## Phase 6: Lot Builder

- [x] Add deterministic low-value/incomplete-card lot assignment recommendations.
- [ ] Generate competing lot strategies.
- [ ] Prevent duplicate active lot assignments.
- [ ] Add locking and lot manifest export.
- [x] Export lot assignment CSV.

## Phase 7: Drafts And eBay Write Integration

- [ ] Add draft queue state machine.
- [ ] Validate unpublished offers.
- [ ] Require approval before Sandbox publishing.
- [ ] Redact API request and response metadata.
- [ ] Add retry and failure recovery.

## Phase 8: Reversible Physical Sorting

- [x] Generate non-destructive file organization/export plans.
- [ ] Detect collisions and estimate disk space.
- [ ] Copy files only after explicit approval.
- [ ] Add move/rename workflow behind explicit confirmation.
- [ ] Save transaction and rollback manifests.
- [ ] Support undo.

## Phase 9: Windows Launcher And Release Controls

- [x] Add `CardOps-Launcher.cmd` double-click entry point.
- [x] Add unified PowerShell WinForms control center.
- [x] Add live, demo, and local-only launch modes.
- [x] Add PID tracking, port checks, and safe tracked-process shutdown.
- [x] Add health, dependency, OCR, eBay, test, and diagnostic controls.
- [x] Add configuration editor with redacted secret handling.
- [x] Add structured launcher logs and redacted diagnostic reports.
- [x] Add Tesseract locate/install/documentation workflow.
- [ ] Add signed installer packaging.
- [ ] Add full GUI automation tests for the launcher.
