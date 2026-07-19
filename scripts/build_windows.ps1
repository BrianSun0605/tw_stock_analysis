param(
    [switch]$Installer
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$env:TWSTOCK_APP_MODE = "dev"
$versionLine = Get-Content -LiteralPath "version.py" |
    Select-String -Pattern '^__version__ = "([^"]+)"$'
if (-not $versionLine) {
    throw "version.py 缺少 __version__"
}
$appVersion = $versionLine.Matches[0].Groups[1].Value
$env:TWSTOCK_VERSION = $appVersion

python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "目前 Python 環境未安裝 PyInstaller；請先執行 python -m pip install pyinstaller==6.20.0"
}

python -m pip check
if ($LASTEXITCODE -ne 0) { throw "pip check 失敗" }
python -m ruff check .
if ($LASTEXITCODE -ne 0) { throw "ruff check 失敗" }
python -m pytest -q -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw "pytest 失敗" }
foreach ($javascript in @(
    "static\js\api.js",
    "static\js\app.js",
    "static\js\dom.js",
    "static\js\export.js",
    "static\js\render.js",
    "static\service-worker.js"
)) {
    node --check $javascript
    if ($LASTEXITCODE -ne 0) { throw "JavaScript 語法檢查失敗：$javascript" }
}
$env:TWSTOCK_APP_MODE = "release"
$env:TWSTOCK_DATA_ROOT = Join-Path $projectRoot "build\appdata"
python -m PyInstaller --noconfirm --clean "packaging\tw_stock_analysis.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build 失敗" }
Remove-Item Env:TWSTOCK_DATA_ROOT -ErrorAction SilentlyContinue

$releaseDir = Join-Path $projectRoot "release"
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
$portable = Join-Path $releaseDir "TWStockAnalysis-portable-$appVersion.zip"
Compress-Archive -Path "dist\TWStockAnalysis\*" -DestinationPath $portable -Force

if ($Installer) {
    $iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
    $isccPath = if ($iscc) { $iscc.Source } else { $null }
    if (-not $isccPath) {
        $programFilesX86 = [Environment]::GetFolderPath("ProgramFilesX86")
        $isccCandidates = @(
            (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
            (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
            (Join-Path $programFilesX86 "Inno Setup 6\ISCC.exe")
        )
        $isccPath = $isccCandidates |
            Where-Object { $_ -and (Test-Path -LiteralPath $_) } |
            Select-Object -First 1
    }
    if (-not $isccPath) {
        throw "找不到 Inno Setup iscc.exe；portable ZIP 已完成，但 installer 尚未建立。"
    }
    & $isccPath "packaging\installer.iss"
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup build 失敗" }
}

$artifacts = Get-ChildItem -LiteralPath $releaseDir -File |
    Where-Object { $_.Extension -in ".zip", ".exe" }
$hashPath = Join-Path $releaseDir "SHA256SUMS.txt"
$lines = foreach ($artifact in $artifacts) {
    $hash = Get-FileHash -LiteralPath $artifact.FullName -Algorithm SHA256
    "$($hash.Hash.ToLowerInvariant())  $($artifact.Name)"
}
Set-Content -LiteralPath $hashPath -Value $lines -Encoding utf8
Write-Host "Build 完成：$releaseDir"
Get-Content -LiteralPath $hashPath
