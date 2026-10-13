param(
    [string]$LabCompose = (Join-Path (Split-Path $PSScriptRoot -Parent) 'KRR\demos\docker-compose.yml')
)

$ErrorActionPreference = 'Stop'
$resolvedLabCompose = (Resolve-Path -LiteralPath $LabCompose).Path
$overridePath = Join-Path $PSScriptRoot 'docker-compose.fuseki.yml'
$previousProjectRoot = $env:OULAD_PROJECT_ROOT
try {
    $env:OULAD_PROJECT_ROOT = $PSScriptRoot.Replace('\', '/')
    # Base file first: retain the existing Compose project and persistent lab volume.
    & docker compose -f $resolvedLabCompose -f $overridePath up -d fuseki
    if ($LASTEXITCODE -ne 0) { throw 'Could not start Fuseki. Check that Docker Desktop is running.' }

    $ready = $false
    for ($attempt = 0; $attempt -lt 15; $attempt++) {
        try {
            $server = Invoke-RestMethod -Uri 'http://127.0.0.1:3030/$/server' -TimeoutSec 2
            $names = @($server.datasets | ForEach-Object { $_.'ds.name' })
            if ($names -contains '/kr' -and $names -contains '/oulad') {
                $ready = $true
                break
            }
        } catch { }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw 'Fuseki has not exposed both datasets yet. Check: docker logs demos-fuseki-1' }
    Write-Output 'Fuseki ready: http://localhost:3030/ (select /oulad).'
    Write-Output 'Next: python src/graph/load_fuseki.py'
} finally {
    if ($null -eq $previousProjectRoot) {
        Remove-Item Env:OULAD_PROJECT_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:OULAD_PROJECT_ROOT = $previousProjectRoot
    }
}
