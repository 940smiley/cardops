# CardOps Launcher Reference

`CardOps-Launcher.cmd` is the primary Windows entry point. It resolves the repository root from its own location, prefers PowerShell 7 (`pwsh`) when available, falls back to Windows PowerShell, and starts `tools/CardOps-Launcher.ps1`.

The launcher does not request administrator rights for normal use. Installation actions that may require system changes show the source and require confirmation.

## Tabs And Controls

| Tab | Control | Action |
| --- | --- | --- |
| Launch | Launch Live Edition | Starts API, worker, and web with demo off and local-only off. Live eBay publishing remains disabled unless explicitly configured elsewhere. |
| Launch | Launch Demo Edition | Starts an isolated demo database and local/mock providers. |
| Launch | Launch Local-Only Edition | Starts the stack with online provider calls disabled. |
| Launch | Launch Frontend | Starts Vite only. |
| Launch | Launch Backend/API | Starts FastAPI only. |
| Launch | Launch Full Stack | Starts local-only API, worker, and frontend. |
| Launch | Stop CardOps Processes | Stops only tracked CardOps process trees after confirmation. |
| Launch | Restart CardOps | Stops tracked processes and starts a local-only stack. |
| Launch | Open CardOps in Browser | Opens the configured local web URL. |
| Launch | Open Project/Data/Logs | Opens the corresponding local directories. |
| Tests and Diagnostics | Run Health Check | Validates `/health` returns an HTTP response. |
| Tests and Diagnostics | Test Backend/API | Runs backend pytest tests. |
| Tests and Diagnostics | Test Frontend | Runs frontend Vitest tests. |
| Tests and Diagnostics | Test Database | Runs Alembic database status. |
| Tests and Diagnostics | Test OCR/Tesseract | Checks local OCR dependency detection. |
| Tests and Diagnostics | Test Image Processing | Runs image ingestion tests. |
| Tests and Diagnostics | Test Card Identification | Runs local identification tests. |
| Tests and Diagnostics | Test Pricing Providers | Runs pricing/listing recommendation tests. |
| Tests and Diagnostics | Test eBay Connection | Runs OAuth redirect diagnostics. |
| Tests and Diagnostics | Run Unit/Integration/Smoke/All Tests | Runs the repository test script or focused tests. |
| Tests and Diagnostics | Check Ports | Reports API and web port listeners. |
| Tests and Diagnostics | Check Dependencies | Reports required and optional tools. |
| Tests and Diagnostics | Generate Diagnostic Report | Saves a redacted JSON report under `logs/launcher/`. |
| Setup | Install Missing Required Items | Runs `scripts/setup.ps1`. |
| Setup | Repair Environment | Re-runs dependency setup and migrations. |
| Setup | Install Python/Node Dependencies | Runs `uv sync` or `pnpm install`. |
| Setup | Install Tesseract | Prompts, then uses `winget` package `UB-Mannheim.TesseractOCR` when approved. |
| Setup | Locate Existing Tesseract | Saves `CARDOPS_TESSERACT_CMD` to the local env file. |
| Setup | Install OCR Language Data | Opens official Tesseract language data documentation. |
| Setup | Initialize Database / Run Migrations | Initializes or migrates SQLite. |
| Setup | Build Production Frontend | Runs the Vite production build. |
| Setup | Clear Safe Caches | Removes test and tool caches only. |
| Configuration | Save/Reload/Validate Settings | Edits local `.ENV` with secrets blanked in the GUI. |
| Configuration | Reset to Safe Defaults | Enables demo/local-only defaults and disables cloud/live publishing. |
| Configuration | Import Configuration | Imports key/value settings from a selected file. |
| Configuration | Export Redacted Configuration | Saves a diagnostic report with credentials redacted. |
| Providers | Refresh Provider Status | Shows configured local/online provider capabilities. |
| Providers | Test eBay OAuth | Runs redirect and Pages diagnostics. |
| Providers | Test Local OCR | Checks Tesseract. |
| Providers | Open Setup Docs | Opens provider documentation pages. |
| Logs | Copy Output / Save Diagnostics / Open Logs | Manages launcher diagnostics and output. |

## Logs And State

- Logs: `logs/launcher/launcher-YYYYMMDD.jsonl`
- Process state: `logs/launcher/process-state.json`
- Diagnostic reports: `logs/launcher/diagnostic-YYYYMMDD-HHMMSS.json`

Logs and reports are ignored by Git. Credentials are redacted before writing.

## Process Safety

The launcher records PIDs for API, worker, and frontend processes it starts. Stop actions use the PID state and command line checks before terminating a process tree. It does not kill unrelated processes by executable name.

If a CardOps port is occupied by an untracked process, the launcher reports the conflict instead of killing it automatically.
