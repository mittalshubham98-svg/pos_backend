# Polls an EAS build until it finishes, then prints its status and APK link.
# Usage: powershell -File mobile\scripts\wait-for-build.ps1 <build-id>
param([Parameter(Mandatory = $true)][string]$BuildId)

Set-Location (Join-Path $PSScriptRoot '..')
for ($i = 0; $i -lt 60; $i++) {
    $json = npx --yes eas-cli@latest build:view $BuildId --json 2>$null | Out-String
    try { $b = $json | ConvertFrom-Json } catch { $b = $null }
    if ($b -and $b.status -in 'FINISHED', 'ERRORED', 'CANCELED') {
        "status: $($b.status)"
        if ($b.artifacts.buildUrl) { "apk: $($b.artifacts.buildUrl)" }
        if ($b.error) { "error: $($b.error.message)" }
        exit 0
    }
    if ($b) { "$(Get-Date -Format HH:mm) still $($b.status)" }
    Start-Sleep -Seconds 60
}
"gave up waiting after an hour"
