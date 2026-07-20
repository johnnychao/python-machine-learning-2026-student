param(
    [string]$ImportSource,
    [string]$Font,
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$scriptPath = Join-Path $PSScriptRoot "build_student_handouts.py"
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue

if (-not $pythonCommand) {
    throw "找不到 Python。請先安裝 Python 3.11 以上版本。"
}

$arguments = @("-X", "utf8", $scriptPath)
if ($ImportSource) {
    $arguments += @("--import-source", (Resolve-Path -LiteralPath $ImportSource).Path)
}
if ($Font) {
    $arguments += @("--font", (Resolve-Path -LiteralPath $Font).Path)
}
if ($VerifyOnly) {
    $arguments += "--verify-only"
}

Push-Location $repoRoot
try {
    & $pythonCommand.Source @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "學生講義建置失敗，結束代碼：$LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
