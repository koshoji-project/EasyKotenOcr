# build_dist.ps1 — 配布用 ZIP（EasyKotenSetup-v2.1.0.zip）の生成
# 使い方: powershell -NoProfile -ExecutionPolicy Bypass -File build_dist.ps1
# 仕様 §2.1: ホイール・モデルは同梱しない（オンラインDL必須）。
#            同梱するのは セットアップ.bat / setup\ / README のみ。
# §13 T1: 全テキストファイル（.bat/.ps1/.py/.json/.txt）に UTF-8 BOM があることを
#         このスクリプトが配布前に検査する。
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$ver = "2.1.0"
$stage = Join-Path $root "build\dist-stage\EasyKotenSetup-v$ver"
$zip = Join-Path $root "build\EasyKotenSetup-v$ver.zip"

if (Test-Path -LiteralPath (Join-Path $root "build\dist-stage")) {
    Remove-Item -LiteralPath (Join-Path $root "build\dist-stage") -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $stage | Out-Null

# 同梱物: dist\ の直下ファイル（セットアップ.bat / README）＋ 開発ツリーの setup\
foreach ($f in Get-ChildItem -LiteralPath (Join-Path $root "dist") -File) {
    Copy-Item -LiteralPath $f.FullName -Destination $stage
}
Copy-Item -LiteralPath (Join-Path $root "setup") -Destination (Join-Path $stage "setup") -Recurse -Force
# tools\（MinGit キャッシュ等・実行時にダウンロード）と __pycache__ は配布しない
foreach ($junk in @("setup\tools", "setup\__pycache__")) {
    $jp = Join-Path $stage $junk
    if (Test-Path -LiteralPath $jp) { Remove-Item -LiteralPath $jp -Recurse -Force }
}

# --- BOM 検査（§13 T1 / §6.1 の落とし穴） ---
$bomFail = @()
Get-ChildItem -LiteralPath $stage -Recurse -File | Where-Object { $_.Extension -in ".bat", ".ps1", ".py", ".json", ".txt" } | ForEach-Object {
    $b = [System.IO.File]::ReadAllBytes($_.FullName)
    if (-not ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF)) {
        $bomFail += $_.FullName
    }
}
if ($bomFail) {
    Write-Host "❌ UTF-8 BOM 不足（PS5.1 が Shift-JIS 誤読で壊れます）。fix_bom.ps1 を実行してください:" -ForegroundColor Red
    $bomFail | ForEach-Object { Write-Host "   $_" }
    exit 1
}
Write-Host "BOM 検査: OK"

# --- 構文検査（PS parser） ---
$psFail = @()
Get-ChildItem -LiteralPath $stage -Recurse -Filter "*.ps1" | ForEach-Object {
    $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$null, [ref]$errors)
    if ($errors) { $psFail += "$($_.Name): $($errors[0].Message) (行 $($errors[0].Extent.StartLineNumber))" }
}
if ($psFail) {
    Write-Host "❌ PowerShell 構文エラー:" -ForegroundColor Red
    $psFail | ForEach-Object { Write-Host "   $_" }
    exit 1
}
Write-Host "構文検査: OK"

Compress-Archive -Path $stage -DestinationPath $zip -CompressionLevel Optimal -Force
Write-Host "✅ 配布 ZIP 生成: $zip"
Get-Item -LiteralPath $zip | ForEach-Object { Write-Host ("   サイズ: {0:N1} MB" -f ($_.Length / 1MB)) }
