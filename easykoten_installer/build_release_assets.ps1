# build_release_assets.ps1 — GitHub Releases v2.1.0 用アセットの生成（仕様 §2.2・2026-11-22 単一zip化）
# C:\easykotenocr\wheels\ の中身（自前ビルド mmcv/mmengine/mmpretrain と SHA256SUMS.txt）を
# 1つの zip「wheels-built-v<ver>.zip」にまとめる。zip 内は wheels/... 相対パスを維持し、
# インストーラー（steps.ps1 Step4）がリポジトリルートへ展開して SHA256 検証する。
# torch / onnxruntime 等は含まない（profile の index 指定で uv sync がオンライン解決）。
# 使い方: powershell -NoProfile -ExecutionPolicy Bypass -File build_release_assets.ps1 [-RepoRoot C:\easykotenocr]
# 出力: <RepoRoot>\easykoten_installer\build\release-assets\wheels-built-v<ver>.zip（gh release upload 用）
param([string]$RepoRoot = "C:\easykotenocr")
$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch { }

$ver = "2.1.0"
$wheels = Join-Path $RepoRoot "wheels"
$manifest = (Get-Content -LiteralPath (Join-Path $RepoRoot "easykoten_installer\setup\manifest.json") -Raw -Encoding UTF8) | ConvertFrom-Json
$zipName = $manifest.wheel_archive.zip
$out = Join-Path $RepoRoot "easykoten_installer\build\release-assets"
$stage = Join-Path $RepoRoot "easykoten_installer\build\release-stage"
if (Test-Path -LiteralPath $out) { Remove-Item -LiteralPath $out -Recurse -Force }
if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $out | Out-Null

# --- SHA256SUMS.txt を再生成（全ホイール。行書式: <64hex>  wheels/<rel> / LF / BOMなし） ---
$allWheels = Get-ChildItem -LiteralPath $wheels -Recurse -Filter *.whl | Sort-Object FullName
if (-not $allWheels) { Write-Host "wheels\ にホイールがありません"; exit 1 }
$sumLines = foreach ($w in $allWheels) {
    $rel = "wheels/" + $w.FullName.Substring($wheels.Length + 1).Replace("\", "/")
    $h = (Get-FileHash -LiteralPath $w.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    "$h  $rel"
}
[System.IO.File]::WriteAllText((Join-Path $wheels "SHA256SUMS.txt"), ($sumLines -join "`n") + "`n", (New-Object System.Text.UTF8Encoding($false)))
Write-Host ("SHA256SUMS.txt 再生成: {0} 行" -f $sumLines.Count)

# --- 単一 zip 生成（staged copy: wheels/ 相対パスを保持） ---
$stageWheels = Join-Path $stage "wheels"
Copy-Item -LiteralPath $wheels -Destination $stageWheels -Recurse
# 注意: PS5.1 では -LiteralPath と -Include の併用で -Include が無視される
# （全ファイルが列挙され Remove される事故になる）。Where-Object で明示フィルタする。
Get-ChildItem -LiteralPath $stageWheels -Recurse -Force |
    Where-Object { $_.Name -eq "__pycache__" -or $_.Extension -eq ".pyc" } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
if ((Get-ChildItem -LiteralPath $stageWheels -Recurse -File).Count -eq 0) { Write-Host "FATAL: stage が空です"; exit 1 }
Compress-Archive -Path $stageWheels -DestinationPath (Join-Path $out $zipName) -CompressionLevel Optimal
$zipPath = Join-Path $out $zipName
if (-not (Test-Path -LiteralPath $zipPath)) { Write-Host "FATAL: zip が生成されませんでした: $zipPath"; exit 1 }
Remove-Item -LiteralPath $stage -Recurse -Force
if (-not (Test-Path -LiteralPath $zipPath)) { Write-Host "FATAL: zip が stage 削除後に消えました: $zipPath"; exit 1 }

Write-Host ""
Write-Host "✅ アセット生成完了: $out"
Get-ChildItem -LiteralPath $out -Filter *.zip | ForEach-Object {
    Write-Host ("   {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
Write-Host ""
Write-Host "アップロード例:"
Write-Host "  gh release upload v$ver --repo koshoji-project/EasyKotenOcr --clobber $out\$zipName"
