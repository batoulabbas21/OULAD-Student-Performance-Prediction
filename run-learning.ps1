$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    & python src/learning/run.py
    if ($LASTEXITCODE -ne 0) { throw 'Learning run failed. Read its failure.json and terminal error.' }
    & python evaluation/verify_learning.py
    if ($LASTEXITCODE -ne 0) { throw 'Saved learning evidence verification failed.' }
    Write-Host 'Session 6 completed. Open outputs/learning/learning-results.html.'
} finally { Pop-Location }
