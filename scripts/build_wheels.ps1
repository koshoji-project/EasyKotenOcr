<#
.SYNOPSIS
  flavor 単位のビルド済み wheel（現状は mmcv のみ）を作る。
.DESCRIPTION
  差分は profiles\flavors.toml からのみ取る。スクリプト内に CUDA path・
  TORCH_CUDA_ARCH_LIST・arch を直書きしない。

  手順:
    1. vendor\mmcv-patches\stage_mmcv.py で素の mmcv checkout をステージング
       （5 オペ除外 + local version tag）
    2. setup.py を mmcv_setup_py315.py（C++20 / USE_CUDA マクロ）で差し替え
    3. vcvars64 + CUDA + flavor venv の python で bdist_wheel
    4. 生成された wheel を wheels\<flavor>\ に置き、SHA256 を表示
.EXAMPLE
  powershell -File scripts\build_wheels.ps1 -Flavor win11-amd64-cu134
#>
param(
    [Parameter(Mandatory = $true)][string]$Flavor,
    [string]$Suffix = 'easykotenocr.3',
    [switch]$SkipStage,
    # ninja の並列数。CUDA ビルドは nvcc 1 プロセスが数 GB の RAM を使うため、
    # 統一メモリ 30GB 環境（RTX Spark N1X）ではデフォルト（= CPU コア数 20）だと
    # "Catastrophic error: out of memory" になる（2026-11-20 実測）。0 = 指定しない。
    [int]$MaxJobs = 4
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$flavorsToml = Join-Path $root 'profiles\flavors.toml'
$profileDir  = Join-Path $root "profiles\$Flavor"
$venvPy      = Join-Path $root "build\$Flavor\venv\Scripts\python.exe"

if (-not (Test-Path $flavorsToml)) { throw "flavors.toml が見つからない: $flavorsToml" }
if (-not (Test-Path $profileDir))  { throw "flavor プロジェクトが無い: $profileDir" }
if (-not (Test-Path $venvPy))      { throw "flavor venv が無い: $venvPy（先に uv sync --project profiles\$Flavor）" }

# PowerShell に TOML パーサは無いので、flavor venv の python を使ったヘルパ経由で読む
$json = & $venvPy (Join-Path $PSScriptRoot 'flavor_info.py') --flavor $Flavor
$f = $json | ConvertFrom-Json
if (-not $f) { throw "flavors.toml に $Flavor が定義されていない" }

$buildDir = Join-Path $root "build\$Flavor"
$staging  = Join-Path $buildDir 'staging\mmcv'
$logDir   = Join-Path $buildDir 'logs'
$wheelDir = Join-Path $root "wheels\$Flavor"
New-Item -ItemType Directory -Force -Path $staging, $logDir, $wheelDir | Out-Null

Write-Output "flavor   : $Flavor"
Write-Output "arch     : $($f.arch)"
Write-Output "cuda_home: $($f.cuda_home)"
Write-Output "arch_list: $($f.torch_cuda_arch_list)"
Write-Output "staging  : $staging"

if (-not $SkipStage) {
    & $venvPy (Join-Path $root 'vendor\mmcv-patches\stage_mmcv.py') --src (Join-Path $root 'mmcv') --dst $staging --suffix $Suffix
    if ($LASTEXITCODE -ne 0) { throw "staging 失敗 (exit $LASTEXITCODE)" }
}
# C++20 / /Zc:preprocessor / USE_CUDA マクロ入りの setup.py で差し替える。
# -SkipStage でも必ず適用する（パッチだけを直して再ビルドする運用があるため）。
Copy-Item (Join-Path $root 'scripts\mmcv_setup_py315.py') (Join-Path $staging 'setup.py') -Force

# vcvars64 を効かせたままビルドするには cmd バッチに落とすのが確実
$logFile = Join-Path $logDir ("mmcv_build_{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
$bat = Join-Path $buildDir 'build_mmcv.bat'
$lines = @('@echo off', "call `"$($f.vcvars)`" >nul", 'set "DISTUTILS_USE_SDK=1"', 'set "MMCV_WITH_OPS=1"',
          # MSVC のメッセージを英語に固定する。torch 2.15 の ABI チェックは cl のバージョン
          # 出力を oem コーデックで読むため、日本語（cp932）出力だと UnicodeDecodeError になる。
          'set "VSLANG=1033"',
          # 現行の VS Build Tools (14.4x) は cl の usage バナーを UTF-8 の日本語で出す。
          # Python 3.15 の oem コーデック（OEM CP = 932）ではそれを復号できず、
          # torch 2.15 の cpp_extension._check_abi が UnicodeDecodeError で死ぬ。
          # ABI チェックは「warning を出すだけ」なので、ここでは明示的に無効化する
          # （torch 公式 wheel + VS2022 の組み合わせは ABI 互換が保証されている）。
          'set "TORCH_DONT_CHECK_COMPILER_ABI=1"')
if ($f.cuda_home) {
    $lines += "set `"CUDA_HOME=$($f.cuda_home)`""
    $lines += 'set "PATH=%CUDA_HOME%\bin;%PATH%"'
}
if ($f.torch_cuda_arch_list) { $lines += "set `"TORCH_CUDA_ARCH_LIST=$($f.torch_cuda_arch_list)`"" }
# device=cpu の flavor: GPU を隠して setup.py を CPU 分岐へ落とす
# （mmcv setup.py は torch.cuda.is_available() で CUDA/CPU を判定するため、
#  GPU が見える CUDA-capable torch 環境では CUDA ビルドになる。
#  CPU flavor の wheel は CPU-only _ext にする）。
if ($f.device -eq 'cpu') { $lines += 'set "CUDA_VISIBLE_DEVICES="' }
if (Get-Command ninja -ErrorAction SilentlyContinue) { $lines += 'set "USE_NINJA=1"' }
if ($MaxJobs -gt 0) { $lines += "set `"MAX_JOBS=$MaxJobs`"" }
$lines += "cd /d `"$staging`""
$lines += "`"$venvPy`" setup.py bdist_wheel > `"$logFile`" 2>&1"
$lines += 'set "RC=%ERRORLEVEL%"'
$lines += '>> ' + '"' + $logFile + '" echo EXIT=%RC%'
# echo は %ERRORLEVEL% を消すので、ビルドの終了コードを呼び出し側へそのまま返す
$lines += 'exit /b %RC%'
Set-Content -Path $bat -Value $lines -Encoding ASCII

Write-Output "build    : $bat"
Write-Output "log      : $logFile"
cmd /c $bat
if ($LASTEXITCODE -ne 0) { throw "ビルド失敗 (exit $LASTEXITCODE)。ログ末尾: `n" + ((Get-Content $logFile -Tail 25) -join "`n") }

$wheel = Get-ChildItem (Join-Path $staging 'dist') -Filter '*.whl' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $wheel) { throw "wheel が見つからない: $staging\dist" }
Copy-Item $wheel.FullName (Join-Path $wheelDir $wheel.Name) -Force
$hash = (Get-FileHash -Algorithm SHA256 (Join-Path $wheelDir $wheel.Name)).Hash
Write-Output ""
Write-Output "wheel    : wheels\$Flavor\$($wheel.Name)"
Write-Output "size     : $([math]::Round($wheel.Length / 1MB, 1)) MB"
Write-Output "sha256   : $hash"
