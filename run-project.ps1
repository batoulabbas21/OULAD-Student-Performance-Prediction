param(
    [switch]$AccessOnly,
    [ValidateSet('live','record','replay','catalog')][string]$Mode = 'live',
    [ValidateRange(1024,65525)][int]$Port = 8009,
    [string]$EnvFile = '',
    [string]$Model = 'gemini-3.5-flash-lite',
    [ValidateRange(1,1000)][int]$MaxRequests = 10,
    [switch]$SkipGraphServices,
    [string]$LabCompose = '',
    [switch]$CheckOnly,
    [switch]$NoBrowser,
    [switch]$NoServe
)

# Reuse the activated lab environment; never install packages or create an env.
$ErrorActionPreference = 'Stop'
if (-not $env:CONDA_PREFIX) { throw 'Activate your lab environment first: conda activate M2ENV' }
$projectPython = Join-Path $env:CONDA_PREFIX 'python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) { throw 'The active Conda environment has no python.exe.' }
$projectArgs = @((Join-Path $PSScriptRoot 'src/project/run.py'), '--mode', $Mode,
    '--port', "$Port", '--model', $Model, '--max-requests', "$MaxRequests")
if ($AccessOnly) { $projectArgs += '--access-only' }
if ($SkipGraphServices) { $projectArgs += '--skip-graph-services' }
if ($CheckOnly) { $projectArgs += '--check-only' }
if ($NoBrowser) { $projectArgs += '--no-browser' }
if ($NoServe) { $projectArgs += '--no-serve' }
if ($EnvFile) { $projectArgs += @('--env-file', $EnvFile) }
if ($LabCompose) { $projectArgs += @('--lab-compose', $LabCompose) }
& $projectPython @projectArgs
if ($LASTEXITCODE -ne 0) { throw "Project launcher stopped (exit $LASTEXITCODE). Read the last stage/error above." }
