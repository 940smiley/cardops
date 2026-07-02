param(
    [switch]$VerboseLogging
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "[build] $Message"
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
    Write-Step "Compiling Python packages"
    Invoke-Checked "uv" @(
        "run",
        "python",
        "-m",
        "compileall",
        "apps/api",
        "apps/worker",
        "packages/schemas/python",
        "tests"
    )

    Write-Step "Building frontend"
    Invoke-Checked "corepack" @("pnpm", "--filter", "@cardops/web", "build")

    Write-Step "Build completed"
} catch {
    Write-Host "[build:error] $($_.Exception.Message)" -ForegroundColor Red
    if ($VerboseLogging) { Write-Host $_.ScriptStackTrace }
    exit 1
}
