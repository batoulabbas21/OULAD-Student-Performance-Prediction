# Uses the already active Conda environment. No installation or server required.
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    $steps = @(
        @{ Args = @('src/validation/prepare_examples.py'); Expected = 0 }
        @{ Args = @('src/validation/validate.py'); Expected = 0 }
        @{ Args = @('src/validation/validate.py', '--data', 'evaluation/fixtures/shacl/valid.ttl', '--out', 'outputs/shacl/sample'); Expected = 0 }
        @{ Args = @('src/validation/validate.py', '--data', 'evaluation/fixtures/shacl/broken.ttl', '--out', 'outputs/shacl/broken'); Expected = 1 }
        @{ Args = @('src/validation/validate.py', '--data', 'evaluation/fixtures/shacl/valid.ttl', '--shapes', 'outputs/shacl/examples/oulad-shapes-v0.ttl', '--out', 'outputs/shacl/draft'); Expected = 1 }
        @{ Args = @('evaluation/verify_shacl.py'); Expected = 0 }
    )
    foreach ($step in $steps) {
        $stageArguments = $step.Args
        Write-Host "Running python $($stageArguments -join ' ')"
        & python @stageArguments
        if ($LASTEXITCODE -ne $step.Expected) {
            throw "Unexpected exit code $LASTEXITCODE; expected $($step.Expected)."
        }
    }
    Write-Host 'Session 4 completed. Expected failures were verified, not ignored.'
} finally {
    Pop-Location
}
