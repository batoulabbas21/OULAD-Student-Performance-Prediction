param([switch]$Fixture)
$ErrorActionPreference='Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    & python src/integration/init_config.py
    if ($LASTEXITCODE -ne 0) { throw 'Could not initialize local configuration.' }
    & docker compose --env-file .env.integration -f docker-compose.postgres.yml up -d --wait
    if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop and retry. Check localhost port 5433.' }
    & python src/integration/setup_ontop.py
    if ($LASTEXITCODE -ne 0) { throw 'Ontop setup failed.' }
    if ($Fixture) { & python evaluation/verify_integration.py --fixture }
    else { & python evaluation/verify_integration.py }
    if ($LASTEXITCODE -ne 0) { throw 'Integration verification failed. Inspect the reported run directory.' }
    Write-Host 'Session 5 integration completed.'
} finally { Pop-Location }
