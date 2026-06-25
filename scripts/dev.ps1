param(
    [switch]$StopExisting,
    [switch]$VerboseLogging
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "[dev] $Message"
}

function Get-PortListener($Port) {
    try {
        return Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1
    } catch {
        return $null
    }
}

function Assert-PortAvailable($Port, $Name) {
    $listener = Get-PortListener $Port
    if ($null -eq $listener) {
        return
    }

    $processId = $listener.OwningProcess
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    $processLabel = if ($null -ne $process) {
        "$($process.ProcessName) [$processId]"
    } else {
        "process [$processId]"
    }

    if ($StopExisting) {
        Write-Step "Stopping existing $Name listener on port $Port ($processLabel)"
        Stop-Process -Id $processId -Force -ErrorAction Stop
        Start-Sleep -Milliseconds 500
        if ($null -ne (Get-PortListener $Port)) {
            throw "Port $Port is still in use after stopping $processLabel."
        }
        return
    }

    throw "$Name port $Port is already in use by $processLabel. Stop it or rerun with -StopExisting."
}

function Receive-JobOutput($Job) {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $records = Receive-Job -Job $Job -Keep -ErrorAction Continue 2>&1
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    foreach ($record in $records) {
        if ($record -is [System.Management.Automation.ErrorRecord]) {
            Write-Host "[$($Job.Name):stderr] $($record.ToString())"
        } else {
            Write-Host "[$($Job.Name)] $record"
        }
    }
}

function Invoke-Pnpm {
    if ($null -ne (Get-Command pnpm -ErrorAction SilentlyContinue)) {
        pnpm @args
    } else {
        corepack pnpm @args
    }
}

$jobs = @()
try {
    $env:PYTHONPATH = "apps/api;apps/worker;packages/schemas/python"
    Assert-PortAvailable 8000 "API"
    Assert-PortAvailable 5173 "Web"

    Write-Step "Ensuring database is migrated"
    uv run alembic upgrade head

    Write-Step "Starting API on http://127.0.0.1:8000"
    $jobs += Start-Job -Name "cardops-api" -ScriptBlock {
        Set-Location $using:PWD
        $env:PYTHONPATH = "apps/api;apps/worker;packages/schemas/python"
        uv run uvicorn cardops_api.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 2>&1 |
            ForEach-Object { "$_" }
    }

    Write-Step "Starting worker"
    $jobs += Start-Job -Name "cardops-worker" -ScriptBlock {
        Set-Location $using:PWD
        $env:PYTHONPATH = "apps/api;apps/worker;packages/schemas/python"
        uv run python -m cardops_worker.main 2>&1 |
            ForEach-Object { "$_" }
    }

    Write-Step "Starting web app on http://127.0.0.1:5173"
    $jobs += Start-Job -Name "cardops-web" -ScriptBlock {
        Set-Location $using:PWD
        if ($null -ne (Get-Command pnpm -ErrorAction SilentlyContinue)) {
            pnpm --filter @cardops/web dev -- --host 127.0.0.1 --port 5173 2>&1 |
                ForEach-Object { "$_" }
        } else {
            corepack pnpm --filter @cardops/web dev -- --host 127.0.0.1 --port 5173 2>&1 |
                ForEach-Object { "$_" }
        }
    }

    Write-Step "All processes started. Press Ctrl+C to stop."
    while ($true) {
        foreach ($job in $jobs) {
            Receive-JobOutput $job
            if ($job.State -in @("Failed", "Completed", "Stopped")) {
                throw "Job $($job.Name) exited with state $($job.State)."
            }
        }
        Start-Sleep -Seconds 2
    }
} catch {
    Write-Host "[dev:error] $($_.Exception.Message)" -ForegroundColor Red
    if ($VerboseLogging) { Write-Host $_.ScriptStackTrace }
    exit 1
} finally {
    foreach ($job in $jobs) {
        Stop-Job -Job $job -ErrorAction SilentlyContinue
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
    }
}
