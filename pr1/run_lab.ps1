param(
    [string]$PythonExe = '',
    [switch]$ReuseIndexes
)
$ErrorActionPreference = 'Stop'
if (-not $PythonExe) {
    $candidate = Get-Command python -ErrorAction SilentlyContinue
    if ($candidate) { $PythonExe = $candidate.Source }
    else {
        $runtime = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
        if (Test-Path -LiteralPath $runtime) { $PythonExe = $runtime }
        else { throw '请用 -PythonExe 参数指定 Python 3 可执行文件。' }
    }
}
$labRoot = $PSScriptRoot
if (-not (Get-Command gcc -ErrorAction SilentlyContinue)) { throw '请将 gcc 加入 PATH。' }
$extra = @()
if ($ReuseIndexes) { $extra = @('--reuse-indexes') }
& $PythonExe (Join-Path $labRoot 'code/tests/run_extended.py') @extra
if ($LASTEXITCODE -ne 0) { throw '全集测试失败，请检查 results/logs 和控制台输出。' }
& $PythonExe (Join-Path $labRoot 'code/tests/run_bonus.py') @extra
if ($LASTEXITCODE -ne 0) { throw 'Bonus 测试失败，请检查 results/logs。' }
& $PythonExe (Join-Path $labRoot 'code/tests/make_lab_report.py')
if ($LASTEXITCODE -ne 0) { throw '生成报告素材失败。' }
Write-Host '实验完成。报告素材见 实验记录与报告素材.md，原始日志见 results/logs。'
