# Run from a terminal where your existing lab Conda environment is active.
# Stops on the first failed stage. No dependency installation or services started.
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    $steps = @(
        @{ Script = 'src/preparation/fetch_data.py'; Args = @() }
        @{ Script = 'src/preparation/profiling.py'; Args = @('--raw') }
        @{ Script = 'src/preparation/select_subset.py'; Args = @('--module', 'AAA') }
        @{ Script = 'src/preparation/profiling.py'; Args = @() }
        @{ Script = 'src/graph/convert_to_rdf.py'; Args = @() }
        @{ Script = 'src/validation/validate.py'; Args = @() }
        @{ Script = 'src/graph/run_queries.py'; Args = @() }
        @{ Script = 'src/graph/rdfs_entailment_demo.py'; Args = @() }
        @{ Script = 'evaluation/verify.py'; Args = @() }
    )
    foreach ($step in $steps) {
        Write-Host "Running $($step.Script)"
        $stageArguments = $step.Args
        & python $step.Script @stageArguments
        if ($LASTEXITCODE -ne 0) { throw "Stage failed: $($step.Script)" }
    }
} finally {
    Pop-Location
}
