param(
    [string]$Owner = "",
    [string]$Repo = "",
    [switch]$SkipPagesConfigure,
    [switch]$SkipDiagnostics,
    [switch]$PublishPages,
    [switch]$VerboseLogging
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "[cardops-ebay-fix] $Message"
}

$workspaceTemp = Join-Path (Split-Path -Parent $PSScriptRoot) "data\tmp"
New-Item -ItemType Directory -Force -Path $workspaceTemp | Out-Null
$env:TEMP = $workspaceTemp
$env:TMP = $workspaceTemp

function Invoke-Checked {
    param(
        [string]$File,
        [string[]]$CommandArgs,
        [switch]$AllowFailure
    )
    if ($VerboseLogging) {
        Write-Host "[exec] $File $($CommandArgs -join ' ')"
    }
    & $File @CommandArgs
    if ($LASTEXITCODE -ne 0 -and -not $AllowFailure) {
        throw "Command failed: $File $($CommandArgs -join ' ')"
    }
}

function Invoke-Captured {
    param(
        [string]$File,
        [string[]]$CommandArgs
    )
    if ($VerboseLogging) {
        Write-Host "[exec] $File $($CommandArgs -join ' ')"
    }
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $File @CommandArgs 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    return @{
        ExitCode = $exitCode
        Output = ($output -join "`n").Trim()
    }
}

function Get-CommandPath($Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -ne $cmd) { return $cmd.Source }

    if ($Name -eq "gh") {
        $candidates = @(
            "C:\Program Files\GitHub CLI\gh.exe",
            (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\gh.exe")
        )
        foreach ($candidate in $candidates) {
            if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path -LiteralPath $candidate)) {
                return $candidate
            }
        }
    }
    return $null
}

function Find-EnvPath($Root) {
    $existing = Get-ChildItem -LiteralPath $Root -Force |
        Where-Object { -not $_.PSIsContainer -and $_.Name.ToLowerInvariant() -eq ".env" } |
        Select-Object -First 1
    if ($null -ne $existing) {
        return $existing.FullName
    }
    return (Join-Path $Root ".env")
}

function Read-EnvFile($Path) {
    $map = [ordered]@{}
    if (-not (Test-Path -LiteralPath $Path)) {
        return $map
    }
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trim = $line.Trim()
        if ($trim.Length -eq 0 -or $trim.StartsWith("#") -or -not $trim.Contains("=")) {
            continue
        }
        $index = $trim.IndexOf("=")
        $key = $trim.Substring(0, $index).Trim()
        $value = $trim.Substring($index + 1).Trim()
        $map[$key] = $value
    }
    return $map
}

function Write-EnvFile($Path, $Values) {
    $orderedKeys = @(
        "CARDOPS_ENV",
        "CARDOPS_DATABASE_URL",
        "CARDOPS_API_HOST",
        "CARDOPS_API_PORT",
        "CARDOPS_WEB_PORT",
        "CARDOPS_DEMO_MODE",
        "CARDOPS_LOG_LEVEL",
        "CARDOPS_LOCAL_ONLY_MODE",
        "CARDOPS_CLOUD_AI_ENABLED",
        "CARDOPS_LIVE_EBAY_PUBLISHING_ENABLED",
        "CARDOPS_PHYSICAL_FILE_MOVES_ENABLED",
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
    $removedKeys = @(
        ("CARDOPS_" + "GCP_PROJECT"),
        ("CARDOPS_" + "GCP_REGION"),
        ("EBAY_" + "CALLBACK_FUNCTION"),
        ("GOOGLE_" + "CLOUD_PROJECT"),
        ("GCLOUD_" + "PROJECT")
    )

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# CardOps AI local defaults")
    foreach ($key in $orderedKeys) {
        if ($Values.Contains($key)) {
            $lines.Add("$key=$($Values[$key])")
        }
    }
    foreach ($key in $Values.Keys) {
        if ($orderedKeys -notcontains $key -and $removedKeys -notcontains $key) {
            $lines.Add("$key=$($Values[$key])")
        }
    }
    Set-Content -LiteralPath $Path -Value $lines -Encoding UTF8
}

function Get-GitHubSlugFromRemote {
    $result = Invoke-Captured "git" @("config", "--get", "remote.origin.url")
    if ($result.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($result.Output)) {
        return $null
    }
    $remote = $result.Output.Trim()
    if ($remote.EndsWith(".git")) {
        $remote = $remote.Substring(0, $remote.Length - 4)
    }
    if ($remote -match "github\.com[:/](?<owner>[^/]+)/(?<repo>[^/]+)$") {
        return @{
            Owner = $Matches.owner
            Repo = $Matches.repo
        }
    }
    return $null
}

function Ensure-StaticPagesFiles($Root) {
    $required = @(
        "public\.nojekyll",
        "public\index.html",
        "public\ebay\callback\index.html"
    )
    foreach ($relative in $required) {
        $fullPath = Join-Path $Root $relative
        if (-not (Test-Path -LiteralPath $fullPath)) {
            throw "Required GitHub Pages file is missing: $relative"
        }
    }
}

function Configure-GitHubPages($Gh, $Owner, $Repo) {
    if ($null -eq $Gh) {
        Write-Step "GitHub CLI was not found; skipping remote Pages configuration"
        return
    }

    Write-Step "Checking GitHub CLI authentication"
    $auth = Invoke-Captured $Gh @("auth", "status")
    if ($auth.ExitCode -ne 0) {
        Write-Step "GitHub CLI is not authenticated; skipping remote Pages configuration"
        return
    }

    $branch = Invoke-Captured $Gh @("api", "repos/$Owner/$Repo/branches/gh-pages", "--jq", ".name")
    if ($branch.ExitCode -ne 0) {
        Write-Step "gh-pages branch is missing; run .\scripts\fix.ps1 -PublishPages to publish the free callback"
        return
    }

    Write-Step "Checking GitHub Pages configuration for $Owner/$Repo"
    $pages = Invoke-Captured $Gh @("api", "repos/$Owner/$Repo/pages")
    if ($pages.ExitCode -eq 0) {
        $pagesConfig = $pages.Output | ConvertFrom-Json
        if (
            $pagesConfig.build_type -eq "legacy" -and
            $null -ne $pagesConfig.source -and
            $pagesConfig.source.branch -eq "gh-pages" -and
            $pagesConfig.source.path -eq "/"
        ) {
            Write-Step "GitHub Pages already serves the gh-pages branch"
            return
        }
        Write-Step "Updating GitHub Pages to serve the gh-pages branch"
        $update = Invoke-Captured $Gh @(
            "api",
            "-X",
            "PUT",
            "repos/$Owner/$Repo/pages",
            "-f",
            "build_type=legacy",
            "-f",
            "source[branch]=gh-pages",
            "-f",
            "source[path]=/"
        )
        if ($update.ExitCode -ne 0) {
            throw "Unable to update GitHub Pages source: $($update.Output)"
        }
        Write-Step "Requesting GitHub Pages build"
        $build = Invoke-Captured $Gh @("api", "-X", "POST", "repos/$Owner/$Repo/pages/builds")
        if ($build.ExitCode -ne 0) {
            Write-Step "GitHub Pages build request was not accepted yet: $($build.Output)"
        }
        return
    }

    Write-Step "Creating GitHub Pages site from the gh-pages branch"
    $create = Invoke-Captured $Gh @(
        "api",
        "-X",
        "POST",
        "repos/$Owner/$Repo/pages",
        "-f",
        "build_type=legacy",
        "-f",
        "source[branch]=gh-pages",
        "-f",
        "source[path]=/"
    )
    if ($create.ExitCode -ne 0) {
        throw "Unable to configure GitHub Pages: $($create.Output)"
    }
    Write-Step "Requesting GitHub Pages build"
    $build = Invoke-Captured $Gh @("api", "-X", "POST", "repos/$Owner/$Repo/pages/builds")
    if ($build.ExitCode -ne 0) {
        Write-Step "GitHub Pages build request was not accepted yet: $($build.Output)"
    }
}

function Publish-PagesFiles($Owner, $Repo) {
    Write-Step "Publishing static public files to the gh-pages branch"
    $root = Split-Path -Parent $PSScriptRoot
    $publishRoot = Join-Path $workspaceTemp "gh-pages-publish"
    $resolvedTemp = [System.IO.Path]::GetFullPath($workspaceTemp)
    $resolvedPublishRoot = [System.IO.Path]::GetFullPath($publishRoot)
    if (-not $resolvedPublishRoot.StartsWith($resolvedTemp, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean unexpected publish directory: $resolvedPublishRoot"
    }
    if (Test-Path -LiteralPath $publishRoot) {
        Remove-Item -LiteralPath $publishRoot -Recurse -Force
    }

    $remoteUrl = "https://github.com/$Owner/$Repo.git"
    $clone = Invoke-Captured "git" @("clone", "--depth", "1", "--branch", "gh-pages", $remoteUrl, $publishRoot)
    if ($clone.ExitCode -ne 0) {
        New-Item -ItemType Directory -Force -Path $publishRoot | Out-Null
        Invoke-Checked "git" @("-C", $publishRoot, "init")
        Invoke-Checked "git" @("-C", $publishRoot, "remote", "add", "origin", $remoteUrl)
        Invoke-Checked "git" @("-C", $publishRoot, "checkout", "--orphan", "gh-pages")
    }

    Get-ChildItem -LiteralPath $publishRoot -Force |
        Where-Object { $_.Name -ne ".git" } |
        Remove-Item -Recurse -Force

    Get-ChildItem -LiteralPath (Join-Path $root "public") -Force |
        Copy-Item -Destination $publishRoot -Recurse -Force

    Invoke-Checked "git" @("-C", $publishRoot, "add", "--all")
    $diff = Invoke-Captured "git" @("-C", $publishRoot, "diff", "--cached", "--quiet", "--")
    if ($diff.ExitCode -eq 0) {
        Write-Step "No gh-pages changes to commit"
    } elseif ($diff.ExitCode -eq 1) {
        Invoke-Checked "git" @("-C", $publishRoot, "commit", "-m", "Deploy free eBay OAuth callback")
        Invoke-Checked "git" @("-C", $publishRoot, "push", "-u", "origin", "gh-pages")
    } else {
        throw "Unable to inspect gh-pages changes: $($diff.Output)"
    }
}

try {
    $root = Split-Path -Parent $PSScriptRoot
    Set-Location -LiteralPath $root

    $slug = Get-GitHubSlugFromRemote
    if ([string]::IsNullOrWhiteSpace($Owner)) {
        $Owner = if ($null -ne $slug) { $slug.Owner } else { "940smiley" }
    }
    if ([string]::IsNullOrWhiteSpace($Repo)) {
        $Repo = if ($null -ne $slug) { $slug.Repo } else { "cardops" }
    }
    $redirectUrl = "https://$Owner.github.io/$Repo/ebay/callback/"

    Write-Step "Final free redirect URL: $redirectUrl"
    Ensure-StaticPagesFiles $root

    $envPath = Find-EnvPath $root
    $envValues = Read-EnvFile $envPath
    $defaults = @{
        CARDOPS_ENV = "development"
        CARDOPS_DATABASE_URL = "sqlite:///./data/cardops.db"
        CARDOPS_API_HOST = "127.0.0.1"
        CARDOPS_API_PORT = "8000"
        CARDOPS_WEB_PORT = "5173"
        CARDOPS_DEMO_MODE = "true"
        CARDOPS_LOG_LEVEL = "INFO"
        CARDOPS_LOCAL_ONLY_MODE = "true"
        CARDOPS_CLOUD_AI_ENABLED = "false"
        CARDOPS_LIVE_EBAY_PUBLISHING_ENABLED = "false"
        CARDOPS_PHYSICAL_FILE_MOVES_ENABLED = "false"
        OPENAI_MODEL_FAST = "gpt-4.1-mini"
        OPENAI_MODEL_ACCURATE = "gpt-4.1"
        EBAY_ENVIRONMENT = "sandbox"
        EBAY_SCOPES = "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.inventory"
        VITE_API_BASE_URL = "http://127.0.0.1:8000"
    }
    foreach ($key in $defaults.Keys) {
        if (-not $envValues.Contains($key)) {
            $envValues[$key] = $defaults[$key]
        }
    }
    $envValues.Remove(("CARDOPS_" + "GCP_PROJECT"))
    $envValues.Remove(("CARDOPS_" + "GCP_REGION"))
    $envValues.Remove(("EBAY_" + "CALLBACK_FUNCTION"))
    $envValues.Remove(("GOOGLE_" + "CLOUD_PROJECT"))
    $envValues.Remove(("GCLOUD_" + "PROJECT"))
    $envValues["EBAY_REDIRECT_URI"] = $redirectUrl
    $envValues["EBAY_AUTH_ACCEPTED_URL"] = $redirectUrl
    $envValues["EBAY_AUTH_DECLINED_URL"] = $redirectUrl
    if (-not $envValues.Contains("EBAY_RUNAME")) {
        $envValues["EBAY_RUNAME"] = ""
    }

    Write-Step "Rewriting .env with corrected callback values while preserving existing secrets"
    Write-EnvFile $envPath $envValues

    Write-Step "Validating OAuth URL builder"
    $env:PYTHONPATH = "apps/api;apps/worker;packages/schemas/python"
    Invoke-Checked "uv" @("run", "python", "-m", "py_compile", "apps/api/cardops_api/ebay_oauth.py")

    if ($PublishPages) {
        Publish-PagesFiles $Owner $Repo
    }

    if ($SkipPagesConfigure) {
        Write-Step "Skipping GitHub Pages configuration by request"
    } else {
        Configure-GitHubPages (Get-CommandPath "gh") $Owner $Repo
    }

    if ($SkipDiagnostics) {
        Write-Step "Skipping diagnostics by request"
    } else {
        Write-Step "Running OAuth diagnostics"
        Invoke-Checked "node" @("scripts/oauth_debug.js") -AllowFailure
    }

    Write-Host ""
    Write-Host "FINAL EBAY DEVELOPER PORTAL VALUES"
    Write-Host "Auth Accepted URL: $redirectUrl"
    Write-Host "Auth Declined URL: $redirectUrl"
    Write-Host "ENV: EBAY_REDIRECT_URI=$redirectUrl"
    Write-Host ""
    Write-Step "Fix script completed"
} catch {
    Write-Host "[cardops-ebay-fix:error] $($_.Exception.Message)" -ForegroundColor Red
    if ($VerboseLogging) {
        Write-Host $_.ScriptStackTrace
    }
    exit 1
}
