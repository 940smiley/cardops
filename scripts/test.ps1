param(
    [switch]$VerboseLogging,
    [switch]$IncludeE2E
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "[test] $Message"
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
    $workspaceTemp = Join-Path (Get-Location) "data\tmp"
    New-Item -ItemType Directory -Force -Path $workspaceTemp | Out-Null
    $env:TEMP = $workspaceTemp
    $env:TMP = $workspaceTemp

    Write-Step "Running backend tests"
    Invoke-Checked "uv" @("run", "pytest", "--basetemp", "data\tmp\pytest-basetemp")

    Write-Step "Running backend lint"
    Invoke-Checked "uv" @("run", "ruff", "check", "apps", "tests")

    Write-Step "Running frontend unit tests"
    Invoke-Checked "corepack" @("pnpm", "--filter", "@cardops/web", "test", "--", "--run")

    Write-Step "Running frontend lint"
    Invoke-Checked "corepack" @("pnpm", "--filter", "@cardops/web", "lint")

    if ($IncludeE2E) {
        Write-Step "Running Playwright workflow tests"
        Invoke-Checked "corepack" @("pnpm", "--filter", "@cardops/web", "test:e2e")
    } else {
        Write-Step "Skipping Playwright workflow tests. Use -IncludeE2E to run them."
    }

    Write-Step "Tests completed"
} catch {
    Write-Host "[test:error] $($_.Exception.Message)" -ForegroundColor Red
    if ($VerboseLogging) { Write-Host $_.ScriptStackTrace }
    exit 1
}
