param(
    [ValidateRange(1024,65535)][int]$Port = 8010,
    [ValidateSet('live','record','catalog')][string]$Mode = 'live',
    [string]$EnvFile = '',
    [string]$Model = 'gemini-3.5-flash-lite',
    [ValidateRange(1,1000)][int]$MaxRequests = 10,
    [switch]$NoBrowser,
    [switch]$Stop
)
$ErrorActionPreference = 'Stop'
$compose = Join-Path $PSScriptRoot 'docker-compose.access.yml'
if (-not $EnvFile) {
    $localConfig = Join-Path $PSScriptRoot '.env.access'
    if (Test-Path -LiteralPath $localConfig) { $EnvFile = $localConfig }
    else { $EnvFile = Join-Path (Split-Path $PSScriptRoot -Parent) 'KRR\demos\.env' }
}
if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) { throw 'Supply -EnvFile pointing to your existing lab .env or project .env.access.' }
$settings = @{ OULAD_GEMINI_ENV_FILE = (Resolve-Path -LiteralPath $EnvFile).Path.Replace('\','/');
    OULAD_ACCESS_PORT = "$Port"; OULAD_ACCESS_MODE = $Mode; OULAD_ACCESS_MODEL = $Model;
    OULAD_ACCESS_MAX_REQUESTS = "$MaxRequests" }
$previousSettings = @{}
foreach ($name in $settings.Keys) { $previousSettings[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
Push-Location -LiteralPath $PSScriptRoot
try {
    foreach ($name in $settings.Keys) { [Environment]::SetEnvironmentVariable($name, $settings[$name], 'Process') }
    if ($Stop) {
        & docker compose -f $compose down
        if ($LASTEXITCODE -ne 0) { throw 'Could not stop the access container.' }
        return
    }
    foreach ($inputFile in @('data/processed/oulad.ttl','ontology/education.rdfs.ttl','shapes/oulad-shapes.ttl')) {
        if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $inputFile) -PathType Leaf)) { throw "Missing $inputFile. Run the project pipeline first." }
    }
    & docker info --format '{{.ServerVersion}}'
    if ($LASTEXITCODE -ne 0) { throw 'Open Docker Desktop, wait for its engine, then retry.' }
    New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot 'outputs/docker-access') | Out-Null
    & docker compose -f $compose up --build -d --wait --wait-timeout 300
    if ($LASTEXITCODE -ne 0) { throw 'Access container did not become healthy. Read: docker compose -f docker-compose.access.yml logs --tail 60 access' }
    $url = "http://127.0.0.1:$Port/"
    Write-Host "Ready: $url | $Mode | up to $MaxRequests API requests per container process."
    Write-Host 'Startup does not call Gemini. Stop with: .\start-access-docker.ps1 -Stop'
    if (-not $NoBrowser) { Start-Process $url }
} finally {
    Pop-Location
    foreach ($name in $settings.Keys) { [Environment]::SetEnvironmentVariable($name, $previousSettings[$name], 'Process') }
}
