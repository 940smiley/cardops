param(
    [string]$Action = "",
    [switch]$SelfTest,
    [switch]$NoGui
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Script:LauncherDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script:RepoRoot = Split-Path -Parent $Script:LauncherDir
$Script:LogDir = Join-Path $Script:RepoRoot "logs\launcher"
$Script:StatePath = Join-Path $Script:LogDir "process-state.json"
$Script:EnvPath = Join-Path $Script:RepoRoot ".ENV"
$Script:ManagedRoles = @("api", "worker", "web")
$Script:LauncherBuildId = "20260624-1700-no-inline-python"
$Script:LauncherOutputBox = $null
$Script:LauncherConfigBox = $null

New-Item -ItemType Directory -Force -Path $Script:LogDir | Out-Null

function Get-LauncherTimestamp {
    return (Get-Date).ToUniversalTime().ToString("o")
}

function Write-LauncherGuiOutput {
    param([string]$Text)
    if ($null -ne $Script:LauncherOutputBox -and -not $Script:LauncherOutputBox.IsDisposed) {
        $Script:LauncherOutputBox.AppendText(("[{0}] {1}`r`n" -f (Get-Date -Format "HH:mm:ss"), $Text))
    } else {
        Write-Host $Text
    }
}

function Redact-Text {
    param([AllowNull()][string]$Text)
    if ($null -eq $Text) { return "" }
    $redacted = $Text
    $patterns = @(
        '(?i)(OPENAI_API_KEY\s*=\s*)[^\s;]+',
        '(?i)(EBAY_CLIENT_SECRET\s*=\s*)[^\s;]+',
        '(?i)(Authorization:\s*Bearer\s+)[A-Za-z0-9._~-]+',
        '(?i)((?:api[_-]?key|token|secret|password)["'']?\s*[:=]\s*["'']?)[^"''\s,;]+',
        '(PRD-[A-Za-z0-9-]{12,})'
    )
    foreach ($pattern in $patterns) {
        $redacted = [regex]::Replace($redacted, $pattern, '$1[REDACTED]')
    }
    return $redacted
}

function Write-LauncherLog {
    param(
        [string]$ActionName,
        [string]$Result,
        [hashtable]$Details = @{}
    )
    $entry = [ordered]@{
        timestamp = Get-LauncherTimestamp
        action = $ActionName
        result = $Result
        cwd = $Script:RepoRoot
        details = $Details
    }
    $json = Redact-Text (($entry | ConvertTo-Json -Depth 8 -Compress))
    $path = Join-Path $Script:LogDir ("launcher-{0}.jsonl" -f (Get-Date -Format "yyyyMMdd"))
    Add-Content -LiteralPath $path -Value $json -Encoding UTF8
}

function Invoke-LogRotation {
    Get-ChildItem -LiteralPath $Script:LogDir -Filter "launcher-*.jsonl" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -Skip 14 |
        Remove-Item -Force -ErrorAction SilentlyContinue
}

function Get-PowerShellHost {
    $pwsh = Get-Command pwsh -ErrorAction SilentlyContinue
    if ($null -ne $pwsh) { return $pwsh.Source }
    return (Get-Command powershell -ErrorAction Stop).Source
}

function ConvertTo-SafeSingleQuoted {
    param([string]$Value)
    return "'{0}'" -f ($Value -replace "'", "''")
}

function Read-EnvFile {
    $map = [ordered]@{}
    if (-not (Test-Path -LiteralPath $Script:EnvPath)) {
        return $map
    }
    foreach ($line in Get-Content -LiteralPath $Script:EnvPath) {
        $trim = $line.Trim()
        if ($trim.Length -eq 0 -or $trim.StartsWith("#") -or -not $trim.Contains("=")) {
            continue
        }
        $index = $trim.IndexOf("=")
        $map[$trim.Substring(0, $index).Trim()] = $trim.Substring($index + 1).Trim()
    }
    return $map
}

function Write-EnvFileAtomic {
    param([hashtable]$Values)
    $existing = Read-EnvFile
    foreach ($key in $Values.Keys) {
        $existing[$key] = $Values[$key]
    }
    $orderedKeys = @(
        "CARDOPS_ENV",
        "CARDOPS_DATABASE_URL",
        "CARDOPS_API_HOST",
        "CARDOPS_API_PORT",
        "CARDOPS_WEB_PORT",
        "CARDOPS_DEMO_MODE",
        "CARDOPS_LOG_LEVEL",
        "CARDOPS_DEFAULT_INPUT_DIR",
        "CARDOPS_DEFAULT_OUTPUT_DIR",
        "CARDOPS_INVENTORY_PATH",
        "CARDOPS_EBAY_EXPORT_PATH",
        "CARDOPS_LOCAL_ONLY_MODE",
        "CARDOPS_CLOUD_AI_ENABLED",
        "CARDOPS_LIVE_EBAY_PUBLISHING_ENABLED",
        "CARDOPS_PHYSICAL_FILE_MOVES_ENABLED",
        "CARDOPS_TESSERACT_CMD",
        "CARDOPS_OCR_LANGUAGE",
        "CARDOPS_CONFIDENCE_THRESHOLD",
        "CARDOPS_DEFAULT_LISTING_FORMAT",
        "OPENAI_API_KEY",
        "OPENAI_MODEL_FAST",
        "OPENAI_MODEL_ACCURATE",
        "EBAY_ENVIRONMENT",
        "EBAY_CLIENT_ID",
        "EBAY_CLIENT_SECRET",
        "EBAY_REDIRECT_URI",
        "EBAY_AUTH_ACCEPTED_URL",
        "EBAY_AUTH_DECLINED_URL",
        "EBAY_RUNAME",
        "EBAY_SCOPES",
        "VITE_API_BASE_URL"
    )
    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# CardOps AI local defaults")
    foreach ($key in $orderedKeys) {
        if ($existing.Contains($key)) {
            $lines.Add("$key=$($existing[$key])")
        }
    }
    foreach ($key in $existing.Keys) {
        if ($orderedKeys -notcontains $key) {
            $lines.Add("$key=$($existing[$key])")
        }
    }
    $tmp = "$Script:EnvPath.tmp"
    Set-Content -LiteralPath $tmp -Value $lines -Encoding UTF8
    Move-Item -LiteralPath $tmp -Destination $Script:EnvPath -Force
    Write-LauncherLog "config.save" "ok" @{ path = $Script:EnvPath }
}

function Invoke-LauncherConfigReload {
    if ($null -eq $Script:LauncherConfigBox -or $Script:LauncherConfigBox.IsDisposed) {
        throw "Configuration editor is not initialized."
    }
    $envMap = Read-EnvFile
    $safeLines = foreach ($key in $envMap.Keys) {
        if ($key -match "(KEY|SECRET|TOKEN|PASSWORD)") {
            "$key="
        } else {
            "$key=$($envMap[$key])"
        }
    }
    $Script:LauncherConfigBox.Text = ($safeLines -join "`r`n")
    return "Configuration reloaded with secrets blanked."
}

function Invoke-LauncherConfigSave {
    if ($null -eq $Script:LauncherConfigBox -or $Script:LauncherConfigBox.IsDisposed) {
        throw "Configuration editor is not initialized."
    }
    $values = @{}
    foreach ($line in $Script:LauncherConfigBox.Lines) {
        if ($line.Trim().Length -eq 0 -or $line.Trim().StartsWith("#") -or -not $line.Contains("=")) { continue }
        $index = $line.IndexOf("=")
        $key = $line.Substring(0, $index).Trim()
        $value = $line.Substring($index + 1).Trim()
        if ($key -match "(KEY|SECRET|TOKEN|PASSWORD)" -and [string]::IsNullOrWhiteSpace($value)) { continue }
        $values[$key] = $value
    }
    Write-EnvFileAtomic $values
    return "Settings saved."
}

function Get-EnvValue {
    param([hashtable]$EnvMap, [string]$Key, [string]$Default = "")
    if ($EnvMap.Contains($Key) -and -not [string]::IsNullOrWhiteSpace($EnvMap[$Key])) {
        return [string]$EnvMap[$Key]
    }
    return $Default
}

function Get-ProcessCommandLine {
    param([int]$ProcessId)
    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
        return [string]$proc.CommandLine
    } catch {
        return ""
    }
}

function Test-Port {
    param([int]$Port)
    try {
        return Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1
    } catch {
        return $null
    }
}

function Read-ProcessState {
    if (-not (Test-Path -LiteralPath $Script:StatePath)) {
        return @{}
    }
    try {
        $json = Get-Content -Raw -LiteralPath $Script:StatePath
        if ([string]::IsNullOrWhiteSpace($json)) { return @{} }
        $raw = $json | ConvertFrom-Json
        $state = @{}
        foreach ($property in $raw.PSObject.Properties) {
            $state[$property.Name] = $property.Value
        }
        return $state
    } catch {
        return @{}
    }
}

function Save-ProcessState {
    param([hashtable]$State)
    $State | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Script:StatePath -Encoding UTF8
}

function Get-DescendantProcessIds {
    param([int]$ProcessId)
    $children = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ParentProcessId -eq $ProcessId }
    $ids = @()
    foreach ($child in $children) {
        $ids += [int]$child.ProcessId
        $ids += Get-DescendantProcessIds -ProcessId ([int]$child.ProcessId)
    }
    return $ids
}

function Test-ManagedProcessSafe {
    param([int]$ProcessId)
    $commandLine = Get-ProcessCommandLine -ProcessId $ProcessId
    return $commandLine -like "*$Script:RepoRoot*" -or $commandLine -like "*cardops*"
}

function Stop-ManagedProcesses {
    param([switch]$Force)
    $state = Read-ProcessState
    $stopped = @()
    foreach ($role in $Script:ManagedRoles) {
        if (-not $state.Contains($role)) { continue }
        $pidValue = [int]$state[$role].pid
        if ($pidValue -le 0 -or -not (Get-Process -Id $pidValue -ErrorAction SilentlyContinue)) {
            $state.Remove($role)
            continue
        }
        if (-not (Test-ManagedProcessSafe -ProcessId $pidValue)) {
            Write-LauncherLog "process.stop.skip" "unsafe" @{ role = $role; pid = $pidValue }
            continue
        }
        $tree = @(Get-DescendantProcessIds -ProcessId $pidValue) + $pidValue
        foreach ($id in ($tree | Select-Object -Unique | Sort-Object -Descending)) {
            try {
                Stop-Process -Id $id -Force:$Force -ErrorAction Stop
                $stopped += $id
            } catch {
                try { Stop-Process -Id $id -Force -ErrorAction Stop; $stopped += $id } catch { }
            }
        }
        $state.Remove($role)
    }
    Save-ProcessState $state
    Write-LauncherLog "process.stop" "ok" @{ pids = $stopped }
    return $stopped
}

function Get-ModeEnvironment {
    param([ValidateSet("live", "demo", "local")] [string]$Mode)
    if ($Mode -eq "live") {
        return @{
            CARDOPS_DEMO_MODE = "false"
            CARDOPS_LOCAL_ONLY_MODE = "false"
            CARDOPS_CLOUD_AI_ENABLED = "false"
            CARDOPS_LIVE_EBAY_PUBLISHING_ENABLED = "false"
        }
    }
    if ($Mode -eq "demo") {
        return @{
            CARDOPS_DEMO_MODE = "true"
            CARDOPS_LOCAL_ONLY_MODE = "true"
            CARDOPS_CLOUD_AI_ENABLED = "false"
            CARDOPS_LIVE_EBAY_PUBLISHING_ENABLED = "false"
            CARDOPS_DATABASE_URL = "sqlite:///./data/cardops-demo.db"
        }
    }
    return @{
        CARDOPS_DEMO_MODE = "false"
        CARDOPS_LOCAL_ONLY_MODE = "true"
        CARDOPS_CLOUD_AI_ENABLED = "false"
        CARDOPS_LIVE_EBAY_PUBLISHING_ENABLED = "false"
    }
}

function New-ManagedCommand {
    param(
        [string]$Command,
        [hashtable]$ModeEnvironment
    )
    $statements = @("Set-Location -LiteralPath $(ConvertTo-SafeSingleQuoted $Script:RepoRoot)")
    foreach ($key in $ModeEnvironment.Keys) {
        $statements += "`$env:$key = $(ConvertTo-SafeSingleQuoted ([string]$ModeEnvironment[$key]))"
    }
    $statements += "`$env:PYTHONPATH = 'apps/api;apps/worker;packages/schemas/python'"
    $statements += $Command
    return "& { $($statements -join '; ') }"
}

function Start-ManagedProcess {
    param(
        [ValidateSet("api", "worker", "web")] [string]$Role,
        [ValidateSet("live", "demo", "local")] [string]$Mode
    )
    $envMap = Read-EnvFile
    $apiPort = [int](Get-EnvValue $envMap "CARDOPS_API_PORT" "8000")
    $webPort = [int](Get-EnvValue $envMap "CARDOPS_WEB_PORT" "5173")
    if ($Role -eq "api" -and (Test-Port $apiPort)) {
        throw "API port $apiPort is already occupied. Use Stop CardOps Processes or change the port."
    }
    if ($Role -eq "web" -and (Test-Port $webPort)) {
        throw "Web port $webPort is already occupied. Use Stop CardOps Processes or change the port."
    }
    $state = Read-ProcessState
    if ($state.Contains($Role)) {
        $pidValue = [int]$state[$Role].pid
        if (Get-Process -Id $pidValue -ErrorAction SilentlyContinue) {
            throw "$Role is already tracked as running with PID $pidValue."
        }
        $state.Remove($Role)
    }
    $modeEnv = Get-ModeEnvironment -Mode $Mode
    $roleCommand = switch ($Role) {
        "api" { "uv run uvicorn cardops_api.main:app --app-dir apps/api --host 127.0.0.1 --port $apiPort" }
        "worker" { "uv run python -m cardops_worker.main" }
        "web" { "corepack pnpm --filter @cardops/web dev -- --host 127.0.0.1 --port $webPort" }
    }
    $command = New-ManagedCommand -Command $roleCommand -ModeEnvironment $modeEnv
    $ps = Get-PowerShellHost
    $stdout = Join-Path $Script:LogDir "$Role-$Mode-out.log"
    $stderr = Join-Path $Script:LogDir "$Role-$Mode-err.log"
    $process = Start-Process -FilePath $ps -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        $command
    ) -WorkingDirectory $Script:RepoRoot -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
    $state[$Role] = [ordered]@{
        pid = $process.Id
        mode = $Mode
        command = Redact-Text $roleCommand
        started_at = Get-LauncherTimestamp
        stdout = $stdout
        stderr = $stderr
    }
    Save-ProcessState $state
    Write-LauncherLog "process.start" "ok" @{ role = $Role; mode = $Mode; pid = $process.Id; command = $roleCommand }
    return $process
}

function Start-CardOpsStack {
    param([ValidateSet("live", "demo", "local")] [string]$Mode)
    Invoke-RepoCommand "setup.db.migrate" "uv run alembic upgrade head" | Out-Null
    Start-ManagedProcess -Role "api" -Mode $Mode | Out-Null
    Start-Sleep -Seconds 2
    Start-ManagedProcess -Role "worker" -Mode $Mode | Out-Null
    Start-ManagedProcess -Role "web" -Mode $Mode | Out-Null
    return "Started $Mode stack."
}

function Invoke-RepoCommand {
    param(
        [string]$ActionName,
        [string]$Command,
        [int]$TimeoutSeconds = 300
    )
    $ps = Get-PowerShellHost
    $safeActionName = $ActionName -replace '[^A-Za-z0-9_.-]', '_'
    $commandScript = Join-Path $Script:LogDir ("command-{0}-{1}.ps1" -f $safeActionName, ([guid]::NewGuid().ToString("N")))
    $scriptLines = @(
        '$ErrorActionPreference = "Stop"',
        "Set-Location -LiteralPath $(ConvertTo-SafeSingleQuoted $Script:RepoRoot)",
        '$env:PYTHONPATH = "apps/api;apps/worker;packages/schemas/python"',
        $Command
    )
    Set-Content -LiteralPath $commandScript -Value $scriptLines -Encoding UTF8
    Write-LauncherLog $ActionName "start" @{ command = $Command }
    try {
        $process = Start-Process -FilePath $ps -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            $commandScript
        ) -WorkingDirectory $Script:RepoRoot -NoNewWindow -PassThru
        if (-not $process.WaitForExit([Math]::Max(1, $TimeoutSeconds) * 1000)) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            Write-LauncherLog $ActionName "timeout" @{ timeout_seconds = $TimeoutSeconds; command = $Command }
            throw "Command timed out after $TimeoutSeconds seconds: $Command"
        }
        Write-LauncherLog $ActionName "completed" @{ exit_code = $process.ExitCode; command = $Command }
        return $process.ExitCode
    } finally {
        Remove-Item -LiteralPath $commandScript -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-RepoPython {
    param(
        [string]$ActionName,
        [string]$Code,
        [int]$TimeoutSeconds = 300
    )
    $safeActionName = $ActionName -replace '[^A-Za-z0-9_.-]', '_'
    $pythonScript = Join-Path $Script:LogDir ("python-{0}-{1}.py" -f $safeActionName, ([guid]::NewGuid().ToString("N")))
    Set-Content -LiteralPath $pythonScript -Value $Code -Encoding UTF8
    try {
        return Invoke-RepoCommand -ActionName $ActionName -Command ("uv run python {0}" -f (ConvertTo-SafeSingleQuoted $pythonScript)) -TimeoutSeconds $TimeoutSeconds
    } finally {
        Remove-Item -LiteralPath $pythonScript -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-LauncherOcrCheck {
    param([string]$ActionName = "test.ocr")
    $code = @'
from cardops_api.card_analysis import detect_tesseract
print(detect_tesseract())
'@
    return Invoke-RepoPython -ActionName $ActionName -Code $code -TimeoutSeconds 60
}

function Invoke-LauncherProviderStatus {
    $code = @'
from cardops_api.providers import detect_capabilities

for provider in detect_capabilities():
    print(provider)
'@
    return Invoke-RepoPython -ActionName "providers.status" -Code $code -TimeoutSeconds 60
}

function Invoke-LauncherDatabaseInit {
    $code = @'
from cardops_api.database import init_db

init_db()
print("database initialized")
'@
    return Invoke-RepoPython -ActionName "setup.db.init" -Code $code -TimeoutSeconds 60
}

function Test-HttpEndpoint {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 8
        return @{ status = "passed"; detail = "HTTP $($response.StatusCode)" }
    } catch {
        return @{ status = "failed"; detail = $_.Exception.Message }
    }
}

function Get-DependencyStatus {
    $items = @()
    foreach ($tool in @("python", "uv", "node", "corepack", "git")) {
        $cmd = Get-Command $tool -ErrorAction SilentlyContinue
        $items += [ordered]@{
            name = $tool
            status = if ($cmd) { "passed" } else { "missing dependency" }
            detail = if ($cmd) { $cmd.Source } else { "Not found on PATH" }
        }
    }
    $tesseract = Get-Command tesseract -ErrorAction SilentlyContinue
    $items += [ordered]@{
        name = "tesseract"
        status = if ($tesseract) { "passed" } else { "missing dependency" }
        detail = if ($tesseract) { $tesseract.Source } else { "Install or locate Tesseract for OCR" }
    }
    return $items
}

function New-DiagnosticReport {
    $envMap = Read-EnvFile
    $state = Read-ProcessState
    $report = [ordered]@{
        generated_at = Get-LauncherTimestamp
        repo_root = $Script:RepoRoot
        dependencies = Get-DependencyStatus
        api = Test-HttpEndpoint "http://127.0.0.1:$(Get-EnvValue $envMap 'CARDOPS_API_PORT' '8000')/health"
        web = Test-HttpEndpoint "http://127.0.0.1:$(Get-EnvValue $envMap 'CARDOPS_WEB_PORT' '5173')"
        process_state = $state
        configuration = @{}
    }
    foreach ($key in $envMap.Keys) {
        $value = [string]$envMap[$key]
        if ($key -match "(KEY|SECRET|TOKEN|PASSWORD)") {
            $report.configuration[$key] = if ($value) { "***" + $value.Substring([Math]::Max(0, $value.Length - 4)) } else { "" }
        } else {
            $report.configuration[$key] = $value
        }
    }
    $path = Join-Path $Script:LogDir ("diagnostic-{0}.json" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
    Redact-Text (($report | ConvertTo-Json -Depth 10)) | Set-Content -LiteralPath $path -Encoding UTF8
    Write-LauncherLog "diagnostic.report" "ok" @{ path = $path }
    return $path
}

function Invoke-SelfTest {
    $results = New-Object System.Collections.Generic.List[object]
    $redacted = Redact-Text "token=TESTSECRETVALUE password=TESTPASSWORDVALUE"
    $results.Add([ordered]@{
        name = "secret redaction"
        status = if ($redacted -notmatch "TESTSECRETVALUE|TESTPASSWORDVALUE") { "passed" } else { "failed" }
        detail = $redacted
    })
    $quoted = ConvertTo-SafeSingleQuoted "D:\Path With Spaces\cardops"
    $results.Add([ordered]@{
        name = "path quoting"
        status = if ($quoted -eq "'D:\Path With Spaces\cardops'") { "passed" } else { "failed" }
        detail = $quoted
    })
    $deps = Get-DependencyStatus
    $results.Add([ordered]@{
        name = "dependency detection"
        status = if ($deps.Count -ge 5) { "passed" } else { "failed" }
        detail = "$($deps.Count) checks"
    })
    $state = Read-ProcessState
    $results.Add([ordered]@{
        name = "state file read"
        status = if ($null -ne $state) { "passed" } else { "failed" }
        detail = $Script:StatePath
    })
    $failed = @($results | Where-Object { $_.status -ne "passed" })
    [ordered]@{ status = if ($failed.Count -eq 0) { "passed" } else { "failed" }; checks = $results } |
        ConvertTo-Json -Depth 6
    if ($failed.Count -gt 0) { exit 1 }
}

function Show-LauncherGui {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    [System.Windows.Forms.Application]::EnableVisualStyles()

    $form = New-Object System.Windows.Forms.Form
    $form.Text = "CardOps Control Center ($Script:LauncherBuildId)"
    $form.Size = New-Object System.Drawing.Size(1120, 760)
    $form.StartPosition = "CenterScreen"

    $tabs = New-Object System.Windows.Forms.TabControl
    $tabs.Dock = "Top"
    $tabs.Height = 500
    $form.Controls.Add($tabs)

    $output = New-Object System.Windows.Forms.TextBox
    $output.Multiline = $true
    $output.ScrollBars = "Vertical"
    $output.ReadOnly = $true
    $output.Dock = "Fill"
    $output.Font = New-Object System.Drawing.Font("Consolas", 9)
    $form.Controls.Add($output)
    $Script:LauncherOutputBox = $output

    function New-TabPage {
        param([string]$Title)
        $page = New-Object System.Windows.Forms.TabPage
        $page.Text = $Title
        $panel = New-Object System.Windows.Forms.FlowLayoutPanel
        $panel.Dock = "Fill"
        $panel.AutoScroll = $true
        $panel.WrapContents = $true
        $panel.Padding = New-Object System.Windows.Forms.Padding(10)
        $page.Controls.Add($panel)
        $tabs.TabPages.Add($page) | Out-Null
        return $panel
    }

    function Add-Button {
        param(
            [System.Windows.Forms.FlowLayoutPanel]$Panel,
            [string]$Text,
            [scriptblock]$OnClick,
            [string]$ToolTip = ""
        )
        $button = New-Object System.Windows.Forms.Button
        $button.Text = $Text
        $button.Width = 210
        $button.Height = 38
        $button.Margin = New-Object System.Windows.Forms.Padding(6)
        if ($ToolTip) {
            $tip = New-Object System.Windows.Forms.ToolTip
            $tip.SetToolTip($button, $ToolTip)
        }
        $clickText = $Text
        $clickAction = $OnClick.GetNewClosure()
        $button.Add_Click({
            try {
                Write-LauncherGuiOutput "Starting: $clickText"
                $result = & $clickAction
                if ($result) {
                    Write-LauncherGuiOutput (Redact-Text ([string]$result))
                }
                Write-LauncherGuiOutput "Completed: $clickText"
            } catch {
                Write-LauncherGuiOutput "FAILED: $($_.Exception.Message)"
                Write-LauncherLog "gui.$clickText" "failed" @{ error = $_.Exception.Message }
            }
        }.GetNewClosure())
        $Panel.Controls.Add($button) | Out-Null
    }

    $launch = New-TabPage "Launch"
    Add-Button $launch "Launch Live Edition" { Start-CardOpsStack "live" } "Uses configured live services but publishing stays disabled."
    Add-Button $launch "Launch Demo Edition" { Start-CardOpsStack "demo" } "Uses demo database and local/mock providers."
    Add-Button $launch "Launch Local-Only Edition" { Start-CardOpsStack "local" } "Disables online provider calls."
    Add-Button $launch "Launch Frontend" { Start-ManagedProcess "web" "local"; "Frontend started." }
    Add-Button $launch "Launch Backend/API" { Start-ManagedProcess "api" "local"; "API started." }
    Add-Button $launch "Launch Full Stack" { Start-CardOpsStack "local" }
    Add-Button $launch "Stop CardOps Processes" {
        if ([System.Windows.Forms.MessageBox]::Show("Stop tracked CardOps processes?", "Confirm", "YesNo") -eq "Yes") {
            Stop-ManagedProcesses -Force
        }
    }
    Add-Button $launch "Restart CardOps" { Stop-ManagedProcesses -Force | Out-Null; Start-CardOpsStack "local" }
    Add-Button $launch "Open CardOps in Browser" {
        $envMap = Read-EnvFile
        Start-Process "http://127.0.0.1:$(Get-EnvValue $envMap 'CARDOPS_WEB_PORT' '5173')"
        "Browser opened."
    }
    Add-Button $launch "Open Project Directory" { Start-Process $Script:RepoRoot; "Project directory opened." }
    Add-Button $launch "Open Data Directory" { Start-Process (Join-Path $Script:RepoRoot "data"); "Data directory opened." }
    Add-Button $launch "Open Logs" { Start-Process $Script:LogDir; "Launcher logs opened." }

    $diagnostics = New-TabPage "Tests and Diagnostics"
    Add-Button $diagnostics "Run Health Check" {
        $envMap = Read-EnvFile
        (Test-HttpEndpoint "http://127.0.0.1:$(Get-EnvValue $envMap 'CARDOPS_API_PORT' '8000')/health" | ConvertTo-Json -Compress)
    }
    Add-Button $diagnostics "Test Backend/API" { Invoke-RepoCommand "test.backend" "uv run pytest tests/api" }
    Add-Button $diagnostics "Test Frontend" { Invoke-RepoCommand "test.frontend" "corepack pnpm --filter @cardops/web test -- --run" }
    Add-Button $diagnostics "Test Database" { Invoke-RepoCommand "test.database" "uv run alembic current" }
    Add-Button $diagnostics "Test OCR" { Invoke-LauncherOcrCheck "test.ocr" }
    Add-Button $diagnostics "Test Tesseract" { (Get-DependencyStatus | Where-Object { $_.name -eq "tesseract" } | ConvertTo-Json -Compress) }
    Add-Button $diagnostics "Test Image Processing" { Invoke-RepoCommand "test.image" "uv run pytest tests/api/test_directory_scan.py" }
    Add-Button $diagnostics "Test Card Identification" { Invoke-RepoCommand "test.identification" "uv run pytest tests/api/test_card_analysis.py" }
    Add-Button $diagnostics "Test Pricing Providers" { Invoke-RepoCommand "test.pricing" "uv run pytest tests/api/test_card_analysis.py -k listing" }
    Add-Button $diagnostics "Test eBay Connection" { Invoke-RepoCommand "test.ebay" "node scripts/oauth_debug.js" }
    Add-Button $diagnostics "Run Unit Tests" { Invoke-RepoCommand "test.unit" ".\scripts\test.ps1" }
    Add-Button $diagnostics "Run Integration Tests" { Invoke-RepoCommand "test.integration" "uv run pytest tests/api" }
    Add-Button $diagnostics "Run Smoke Test" { Invoke-RepoCommand "test.smoke" ".\scripts\test.ps1" }
    Add-Button $diagnostics "Run All Tests" { Invoke-RepoCommand "test.all" ".\scripts\test.ps1" }
    Add-Button $diagnostics "Check Ports" {
        $envMap = Read-EnvFile
        $ports = @((Get-EnvValue $envMap "CARDOPS_API_PORT" "8000"), (Get-EnvValue $envMap "CARDOPS_WEB_PORT" "5173"))
        foreach ($port in $ports) {
            $listener = Test-Port ([int]$port)
            if ($listener) { "Port $port occupied by PID $($listener.OwningProcess)" } else { "Port $port available" }
        }
    }
    Add-Button $diagnostics "Check Dependencies" { Get-DependencyStatus | ConvertTo-Json -Depth 4 }
    Add-Button $diagnostics "Generate Diagnostic Report" { New-DiagnosticReport }

    $setup = New-TabPage "Setup"
    Add-Button $setup "Install Missing Required Items" { Invoke-RepoCommand "setup.install" ".\scripts\setup.ps1" }
    Add-Button $setup "Install Selected Items" { Invoke-RepoCommand "setup.install.selected" ".\scripts\setup.ps1 -SkipPlaywrightBrowsers" }
    Add-Button $setup "Repair Environment" { Invoke-RepoCommand "setup.repair" ".\scripts\setup.ps1" }
    Add-Button $setup "Create/Rebuild Virtual Environment" { Invoke-RepoCommand "setup.venv" "uv sync --extra dev" }
    Add-Button $setup "Install Python Dependencies" { Invoke-RepoCommand "setup.python" "uv sync --extra dev" }
    Add-Button $setup "Install Node Dependencies" { Invoke-RepoCommand "setup.node" "corepack pnpm install" }
    Add-Button $setup "Install Tesseract" {
        if ([System.Windows.Forms.MessageBox]::Show("Install Tesseract OCR through winget package UB-Mannheim.TesseractOCR?", "Confirm source", "YesNo") -eq "Yes") {
            Invoke-RepoCommand "setup.tesseract" "winget install --id UB-Mannheim.TesseractOCR --exact --accept-package-agreements --accept-source-agreements"
        }
    }
    Add-Button $setup "Locate Existing Tesseract" {
        $dialog = New-Object System.Windows.Forms.OpenFileDialog
        $dialog.Filter = "tesseract.exe|tesseract.exe|Executables|*.exe"
        if ($dialog.ShowDialog() -eq "OK") {
            Write-EnvFileAtomic @{ CARDOPS_TESSERACT_CMD = $dialog.FileName }
            "Saved CARDOPS_TESSERACT_CMD."
        }
    }
    Add-Button $setup "Install OCR Language Data" { Start-Process "https://tesseract-ocr.github.io/tessdoc/Data-Files"; "Opened Tesseract language data documentation." }
    Add-Button $setup "Initialize Database" { Invoke-LauncherDatabaseInit }
    Add-Button $setup "Run Migrations" { Invoke-RepoCommand "setup.db.migrate" "uv run alembic upgrade head" }
    Add-Button $setup "Build Production Frontend" { Invoke-RepoCommand "setup.frontend.build" "corepack pnpm --filter @cardops/web build" }
    Add-Button $setup "Clear Safe Caches" {
        foreach ($path in @(".pytest_cache", ".ruff_cache", "apps\web\test-results")) {
            $full = Join-Path $Script:RepoRoot $path
            if (Test-Path -LiteralPath $full) { Remove-Item -LiteralPath $full -Recurse -Force }
        }
        "Safe caches cleared."
    }

    $config = New-TabPage "Configuration"
    $configBox = New-Object System.Windows.Forms.TextBox
    $configBox.Multiline = $true
    $configBox.ScrollBars = "Both"
    $configBox.Width = 980
    $configBox.Height = 300
    $configBox.Font = New-Object System.Drawing.Font("Consolas", 9)
    $config.Controls.Add($configBox) | Out-Null
    $Script:LauncherConfigBox = $configBox
    Add-Button $config "Save Settings" { Invoke-LauncherConfigSave }
    Add-Button $config "Reload Settings" { Invoke-LauncherConfigReload }
    Add-Button $config "Validate Settings" { Invoke-RepoCommand "config.validate" "node scripts/oauth_debug.js" }
    Add-Button $config "Reset to Safe Defaults" {
        Write-EnvFileAtomic @{
            CARDOPS_DEMO_MODE = "true"
            CARDOPS_LOCAL_ONLY_MODE = "true"
            CARDOPS_CLOUD_AI_ENABLED = "false"
            CARDOPS_LIVE_EBAY_PUBLISHING_ENABLED = "false"
            CARDOPS_PHYSICAL_FILE_MOVES_ENABLED = "false"
        }
        Invoke-LauncherConfigReload
    }
    Add-Button $config "Import Configuration" {
        $dialog = New-Object System.Windows.Forms.OpenFileDialog
        $dialog.Filter = "Environment files|*.env;*.txt|All files|*.*"
        if ($dialog.ShowDialog() -eq "OK") {
            $values = @{}
            foreach ($line in Get-Content -LiteralPath $dialog.FileName) {
                if ($line -match '^([^#][^=]+)=(.*)$') { $values[$Matches[1].Trim()] = $Matches[2].Trim() }
            }
            Write-EnvFileAtomic $values
            Invoke-LauncherConfigReload
        }
    }
    Add-Button $config "Export Redacted Configuration" { New-DiagnosticReport }
    Invoke-LauncherConfigReload | Out-Null

    $providers = New-TabPage "Providers"
    Add-Button $providers "Refresh Provider Status" { Invoke-LauncherProviderStatus }
    Add-Button $providers "Test eBay OAuth" { Invoke-RepoCommand "providers.ebay" "node scripts/oauth_debug.js" }
    Add-Button $providers "Test Local OCR" { Invoke-LauncherOcrCheck "providers.ocr" }
    Add-Button $providers "Open eBay Developer Setup" { Start-Process "https://developer.ebay.com/"; "Opened eBay developer portal." }
    Add-Button $providers "Open Tesseract Setup Docs" { Start-Process "https://tesseract-ocr.github.io/tessdoc/"; "Opened Tesseract documentation." }

    $logs = New-TabPage "Logs"
    Add-Button $logs "Copy Output" {
        if ($null -eq $Script:LauncherOutputBox -or $Script:LauncherOutputBox.IsDisposed) {
            throw "Launcher output box is not initialized."
        }
        [System.Windows.Forms.Clipboard]::SetText($Script:LauncherOutputBox.Text)
        "Output copied."
    }
    Add-Button $logs "Save Diagnostics" { New-DiagnosticReport }
    Add-Button $logs "Open Launcher Logs" { Start-Process $Script:LogDir; "Logs opened." }
    Add-Button $logs "Open API Log File" { Start-Process (Join-Path $Script:LogDir "api-local-out.log"); "API log opened." }
    Add-Button $logs "Rotate Logs Now" { Invoke-LogRotation; "Old logs rotated." }

    Write-LauncherGuiOutput "CardOps Launcher ready. Build: $Script:LauncherBuildId. Repo: $Script:RepoRoot"
    [void]$form.ShowDialog()
}

function Invoke-Action {
    param([string]$Name)
    switch ($Name.ToLowerInvariant()) {
        "start-local" { Start-CardOpsStack "local" }
        "start-demo" { Start-CardOpsStack "demo" }
        "start-live" { Start-CardOpsStack "live" }
        "stop" { Stop-ManagedProcesses -Force | ConvertTo-Json }
        "doctor" { Invoke-RepoCommand "cli.doctor" ".\scripts\doctor.ps1" }
        "test" { Invoke-RepoCommand "cli.test" ".\scripts\test.ps1" }
        "report" { New-DiagnosticReport }
        default { throw "Unknown action: $Name" }
    }
}

Invoke-LogRotation

if ($SelfTest) {
    Invoke-SelfTest
    exit 0
}

if ($Action) {
    Invoke-Action $Action
    exit 0
}

if (-not $NoGui) {
    Show-LauncherGui
}
