param(
    [switch]$VerboseLogging,
    [switch]$SkipPlaywrightBrowsers
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "[setup] $Message"
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
    Write-Step "Checking required tools"
    foreach ($tool in @("python", "uv", "node", "corepack")) {
        if ($null -eq (Get-Command $tool -ErrorAction SilentlyContinue)) {
            throw "Required command '$tool' was not found on PATH."
        }
    }

    if ($null -eq (Get-Command pnpm -ErrorAction SilentlyContinue)) {
        Write-Step "Preparing pnpm through Corepack"
        Invoke-Checked "corepack" @("prepare", "pnpm@9.15.4", "--activate")
    }

    Write-Step "Creating data directories"
    New-Item -ItemType Directory -Force -Path "data", "data/demo", "data/thumbnails", "data/exports", "data/backups" | Out-Null

    Write-Step "Installing Python dependencies with uv"
    Invoke-Checked "uv" @("sync", "--extra", "dev")

    Write-Step "Installing frontend dependencies with pnpm"
    Invoke-Checked "corepack" @("pnpm", "install")

    if (-not $SkipPlaywrightBrowsers) {
        Write-Step "Installing Playwright Chromium browser"
        Invoke-Checked "corepack" @("pnpm", "--filter", "@cardops/web", "exec", "playwright", "install", "chromium")
    } else {
        Write-Step "Skipping Playwright browser install"
    }

    Write-Step "Applying database migrations"
    Invoke-Checked "uv" @("run", "alembic", "upgrade", "head")

    Write-Step "Seeding demo data"
    Invoke-Checked "uv" @("run", "python", "-m", "cardops_api.demo", "seed")

    Write-Step "Setup completed"
} catch {
    Write-Host "[setup:error] $($_.Exception.Message)" -ForegroundColor Red
    if ($VerboseLogging) { Write-Host $_.ScriptStackTrace }
    exit 1
}
