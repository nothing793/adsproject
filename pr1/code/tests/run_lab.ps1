param([string]$PythonExe = 'python', [switch]$ReuseIndexes)
$ErrorActionPreference = 'Stop'
$extra = @()
if ($ReuseIndexes) { $extra = @('--reuse-indexes') }
foreach ($script in @('run_extended.py', 'review_regression.py', 'run_bonus.py', 'make_lab_report.py')) {
    $arguments = @()
    if ($script -in @('run_extended.py', 'run_bonus.py')) { $arguments = $extra }
    & $PythonExe (Join-Path $PSScriptRoot $script) @arguments
    if ($LASTEXITCODE -ne 0) { throw "Test failed: $script" }
}
Write-Host 'Tests complete. Results are saved under pr1/results.'
