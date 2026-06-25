param(
    [switch]$DryRun,
    [switch]$VerboseLogging
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "[reset-demo] $Message"
}

function Invoke-Checked {
    param(
        [string]$File,
        [string[]]$CommandArgs
    )
    & $File @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $File $($CommandArgs -join ' ')"
    }
}

try {
    $env:PYTHONPATH = "apps/api;apps/worker;packages/schemas/python"
    $dbPath = Join-Path (Get-Location) "data/cardops.db"
    $thumbPath = Join-Path (Get-Location) "data/thumbnails"
    Write-Step "This resets only CardOps demo database and generated thumbnails."
    if ($DryRun) {
        Write-Step "Dry run: would remove $dbPath if present"
        Write-Step "Dry run: would clear $thumbPath if present"
        Write-Step "Dry run: would run migrations and seed demo data"
        exit 0
    }

    if (Test-Path $dbPath) {
        Remove-Item -LiteralPath $dbPath -Force
    }
    if (Test-Path $thumbPath) {
        Get-ChildItem -LiteralPath $thumbPath -File | Remove-Item -Force
    } else {
        New-Item -ItemType Directory -Force -Path $thumbPath | Out-Null
    }

    Invoke-Checked "uv" @("run", "alembic", "upgrade", "head")
    Invoke-Checked "uv" @("run", "python", "-m", "cardops_api.demo", "seed", "--force")
    Write-Step "Demo reset completed"
} catch {
    Write-Host "[reset-demo:error] $($_.Exception.Message)" -ForegroundColor Red
    if ($VerboseLogging) { Write-Host $_.ScriptStackTrace }
    exit 1
}
