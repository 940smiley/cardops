param(
    [switch]$VerboseLogging
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "[doctor] $Message"
}

function Test-Command($Name, $Hint) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $cmd) {
        Write-Host "[missing] $Name - $Hint" -ForegroundColor Yellow
        return $false
    }
    Write-Host "[ok] $Name -> $($cmd.Source)" -ForegroundColor Green
    return $true
}

try {
    Write-Step "Checking local toolchain"
    $ok = $true
    $ok = (Test-Command "python" "Install Python 3.12 or newer") -and $ok
    $ok = (Test-Command "uv" "Install uv from https://docs.astral.sh/uv/") -and $ok
    $ok = (Test-Command "node" "Install Node.js 20 or newer") -and $ok
    $ok = (Test-Command "npm" "Install Node.js/npm") -and $ok
    $ok = (Test-Command "corepack" "Install Node.js with Corepack support") -and $ok
    $pnpm = Get-Command pnpm -ErrorAction SilentlyContinue
    if ($null -eq $pnpm) {
        Write-Host "[warn] pnpm is not active. setup.ps1 will enable it through Corepack." -ForegroundColor Yellow
    } else {
        Write-Host "[ok] pnpm -> $($pnpm.Source)" -ForegroundColor Green
    }

    Write-Step "Versions"
    python --version
    uv --version
    node --version
    npm --version
    if ($null -ne $pnpm) { pnpm --version }

    if (-not $ok) {
        throw "One or more required tools are missing."
    }
    Write-Step "Doctor completed"
} catch {
    Write-Host "[doctor:error] $($_.Exception.Message)" -ForegroundColor Red
    if ($VerboseLogging) { Write-Host $_.ScriptStackTrace }
    exit 1
}
