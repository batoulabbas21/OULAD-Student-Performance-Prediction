param(
    [ValidateSet('local','record','replay','live')][string]$Mode = 'local',
    [string]$EnvFile = '',
    [string]$Model = '',
    [int]$MaxRequests = 45
)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    & python evaluation/verify_access.py --local-only
    if ($LASTEXITCODE -ne 0) { throw 'Local access checks failed.' }
    if ($Mode -ne 'local') {
        $accessArgs = @('src/access/evaluate.py','--mode',$Mode,'--max-requests',"$MaxRequests")
        if ($EnvFile) { $accessArgs += @('--env-file',$EnvFile) }
        if ($Model) { $accessArgs += @('--model',$Model) }
        & python @accessArgs
        if ($LASTEXITCODE -ne 0) { throw 'Evaluation incomplete. Read the saved report and summary error.' }
        & python evaluation/verify_access.py
        if ($LASTEXITCODE -ne 0) { throw 'Saved access evidence verification failed.' }
        Write-Host 'Open outputs/access/access-results.html.'
    } else { Write-Host 'Open outputs/access/local-results.html. No API calls were made.' }
} finally { Pop-Location }
