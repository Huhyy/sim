param(
    [string]$EnvFile = (Join-Path $PSScriptRoot "..\.env")
)

$ErrorActionPreference = "Stop"

$resolvedEnvFile = [System.IO.Path]::GetFullPath($EnvFile)
if (-not (Test-Path -LiteralPath $resolvedEnvFile -PathType Leaf)) {
    throw "Integration environment file not found: $resolvedEnvFile"
}

foreach ($rawLine in Get-Content -LiteralPath $resolvedEnvFile) {
    $line = $rawLine.Trim()
    if (-not $line -or $line.StartsWith("#")) {
        continue
    }
    if ($line.StartsWith("export ")) {
        $line = $line.Substring(7).Trim()
    }

    $separator = $line.IndexOf("=")
    if ($separator -lt 1) {
        throw "Invalid environment entry. Expected NAME=value."
    }

    $name = $line.Substring(0, $separator).Trim()
    $value = $line.Substring($separator + 1).Trim()
    if ($name -notmatch "^[A-Za-z_][A-Za-z0-9_]*$") {
        throw "Invalid environment variable name: $name"
    }
    if ($name -like "PROLIFIC_*") {
        continue
    }
    if ($value.Length -ge 2) {
        $first = $value[0]
        $last = $value[$value.Length - 1]
        if (($first -eq '"' -and $last -eq '"') -or ($first -eq "'" -and $last -eq "'")) {
            $value = $value.Substring(1, $value.Length - 2)
        }
    }

    [Environment]::SetEnvironmentVariable($name, $value, "Process")
}

$missing = @()
if (-not $env:SUPABASE_URL) {
    $missing += "SUPABASE_URL"
}
if (-not $env:SUPABASE_SECRET_KEY -and -not $env:SUPABASE_SERVICE_ROLE_KEY) {
    $missing += "SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY"
}
if ($missing.Count -gt 0) {
    throw "Missing required integration configuration: $($missing -join ', ')"
}
if ($env:SUPABASE_SECRET_KEY -and $env:SUPABASE_SERVICE_ROLE_KEY) {
    throw "Configure only one of SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY."
}

$serverKey = if ($env:SUPABASE_SECRET_KEY) {
    $env:SUPABASE_SECRET_KEY
} else {
    $env:SUPABASE_SERVICE_ROLE_KEY
}
if ($serverKey.StartsWith("sb_publishable_")) {
    throw "A publishable Supabase key cannot run server-side integration tests."
}

if ($env:RUN_SUPABASE_INTEGRATION -ne "1") {
    throw "RUN_SUPABASE_INTEGRATION must equal 1."
}
if ($env:SUPABASE_INTEGRATION_ALLOW_SYNTHETIC_WRITES -ne "1") {
    throw "SUPABASE_INTEGRATION_ALLOW_SYNTHETIC_WRITES must equal 1."
}
[Environment]::SetEnvironmentVariable("PROLIFIC_API_TOKEN", "", "Process")

Write-Output "Integration environment loaded for this PowerShell process."
Write-Output "Configured: SUPABASE_URL and one server credential."
Write-Output "Prolific credentials are excluded and real payment paths are disabled."
if ($env:SUPABASE_DB_URL) {
    Write-Output "Optional direct database migration access is configured."
} else {
    Write-Output "No direct database URL configured; use the authenticated Supabase SQL Editor for migrations."
}
