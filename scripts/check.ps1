# Local quality gate. Run before every commit. No CI runs in the cloud.
# Each step must exit 0 on its own; the first failure stops the script.
$ErrorActionPreference = "Stop"

foreach ($step in @(
    @("ruff", "format", "--check", "."),
    @("ruff", "check", "."),
    @("mypy", "--strict", "src"),
    @("pytest")
)) {
    & $step[0] $step[1..($step.Length - 1)]
    if ($LASTEXITCODE -ne 0) { throw "$($step -join ' ') failed with exit code $LASTEXITCODE" }
}
