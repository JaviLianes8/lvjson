# Local quality gate. Run before every commit. No CI runs in the cloud.
# Each step must exit 0 on its own; the first failure stops the script.
$ErrorActionPreference = "Stop"

$steps = @(
    @("ruff", "format", "--check", "."),
    @("ruff", "check", "."),
    @("mypy", "--strict", "src", "tests"),
    @("pytest")
)
foreach ($step in $steps) {
    $command = $step[0]
    $arguments = @($step | Select-Object -Skip 1)
    & $command @arguments
    if ($LASTEXITCODE -ne 0) { throw "$($step -join ' ') failed with exit code $LASTEXITCODE" }
}
