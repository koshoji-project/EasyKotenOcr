# setup.ps1 — Easy古典OCR インストーラー本体（INSTALLER_SPEC_v2.1.md §6）
# 使い方:
#   （人間）setup.ps1                     … 対話テキストモード（GUI不可時のフォールバック）
#   （GUI）setup.ps1 -Mode Batch -Dest .. -FlavorId ..   … GUI 子プロセスとして非対話実行
#   （CI）  同上 -Batch
#   （検証）setup.ps1 -PreflightOnly      … ステップ1のみ実行して終了
# 終了コード: 0=成功 / 10..90=各ステップ失敗 / 99=キャンセル
param(
    [ValidateSet("Text", "Batch")] [string]$Mode = "Text",
    [string]$Dest = "",
    [string]$FlavorId = "",
    [string]$GuiLog = "",
    [switch]$PreflightOnly
)
$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch { }

. (Join-Path $PSScriptRoot "lib.ps1")
. (Join-Path $PSScriptRoot "steps.ps1")

# ---- マニフェスト ----
$MF = (Get-Content -LiteralPath (Join-Path $PSScriptRoot "manifest.json") -Raw -Encoding UTF8) | ConvertFrom-Json
$script:MF = $MF

Initialize-Logging -TempLogDir (Join-Path $env:TEMP "EasyKotenSetup")
Write-Log "=== Easy古典OCR セットアップ v$($MF.version) 開始（Mode=$Mode）==="

# ---- ステップ1: 事前チェック ----
Invoke-Step1-Preflight
if ($PreflightOnly) { Write-Log "（事前チェックのみ完了）"; exit 0 }

# ---- フレーバー自動判定（★推奨） ----
$auto = Get-AutoFlavor $MF.flavors
Write-Log "この PC の推奨フレーバー: $($auto.id)"

function Show-FlavorMenu {
    Write-Host ""
    Write-Host "お使いの PC に最も近いものを 1 つ選んで、番号を入力してください。"
    Write-Host "（迷ったら ★ の付いた番号を押して Enter キーを押してください）"
    $i = 1
    foreach ($f in $MF.flavors) {
        $star = if ($f.id -eq $auto.id) { " ★" } else { "  " }
        Write-Host ("  {0}{1} {2}" -f $i, $star, $f.caption)
        $i++
    }
}

function Select-FlavorInteractive {
    Show-FlavorMenu
    while ($true) {
        $ans = Read-Host "番号を入力（1-$($MF.flavors.Count)、Enter で ★推奨）"
        if ($ans -eq "") { return $auto }
        if ($ans -match "^[1-4]$") { return $MF.flavors[[int]$ans - 1] }
        Write-Host "1〜$($MF.flavors.Count) の数字を入力してください。"
    }
}

function Resolve-DestInteractive {
    $default = "C:\easykotenocr"
    Write-Host ""
    Write-Host "インストール先を尋ねます。基本的にそのままで構いません。"
    Write-Host "（よく使う文字以外を含むフォルダーや、OneDrive 同期中は失敗することがあります）"
    while ($true) {
        $ans = Read-Host "インストール先 [Enter で $default]"
        if ($ans -eq "") { $ans = $default }
        $ans = $ans.Trim().Trim('"')
        if (-not [System.IO.Path]::IsPathRooted($ans)) {
            Write-Host "絶対パス（例: C:\easykotenocr）で入力してください。"
            continue
        }
        if ($ans -match "[^\x20-\x7E]") {
            Write-Host "そのまま進むこともできますが、日本語などを含まないフォルダー（例: C:\easykotenocr）をおすすめします。"
        }
        if ($ans -like "$env:USERPROFILE\OneDrive*") {
            Write-Host "注意: OneDrive で同期されているフォルダーです。エラーになりやすいので、C:\easykotenocr などをおすすめします。"
        }
        $drive = Get-PSDrive -Name ([System.IO.Path]::GetPathRoot($ans).Substring(0,1)) -ErrorAction SilentlyContinue
        if ($drive -and ($drive.DriveType -ne "Fixed")) {
            Write-Host "USB メモリやネットワークドライブにはインストールできません。"
            continue
        }
        $free = Get-DriveFreeGB $ans
        $reqGB = 10
        if ($free -ge 0 -and $free -lt $reqGB) {
            Write-Host "そのドライブの空きは ${free}GB です。20GB 以上の空きがある場所を選んでください。"
            continue
        }
        if (Test-Path -LiteralPath $ans) {
            $items = @(Get-ChildItem -LiteralPath $ans -Force -ErrorAction SilentlyContinue)
            if (($items.Count -gt 0) -and -not (Test-Path -LiteralPath (Join-Path $ans "pyproject.toml"))) {
                Write-Host "そのフォルダーは別のファイルで使われています。空のフォルダーを指定してください。"
                continue
            }
        } else {
            try { New-Item -ItemType Directory -Force -Path $ans | Out-Null } catch {
                Write-Host "その場所フォルダーを作れません。別の場所を指定してください。"
                continue
            }
        }
        # 書き込みテスト
        $probe = Join-Path $ans ".easykoten_write_test"
        try { Set-Content -LiteralPath $probe -Value "x" -ErrorAction Stop; Remove-Item -LiteralPath $probe -Force } catch {
            Write-Host "その場所に書き込めません（アクセス権が必要です）。別の場所を指定してください。"
            continue
        }
        return $ans
    }
}

# ---- Q1 / Q2 ----
if ($Mode -eq "Batch") {
    if (-not $Dest) { Fail-Setup 10 "-Batch には -Dest が必要です" $null }
    if (-not $FlavorId) { Fail-Setup 10 "-Batch には -FlavorId が必要です" $null }
    $script:Dest = $Dest
    $fl = $MF.flavors | Where-Object { $_.id -eq $FlavorId } | Select-Object -First 1
    if (-not $fl) { Fail-Setup 10 "不明なフレーバーです: $FlavorId" $null }
    $script:Flavor = $fl
} else {
    $script:Dest = Resolve-DestInteractive
    $script:Flavor = Select-FlavorInteractive
    Write-Host ""
    Write-Host "インストール先: $script:Dest"
    Write-Host "環境: $($script:Flavor.caption)（$($script:Flavor.id)）"
    $ok = Read-Host "この内容で開始しますか？ [Y]"
    if ($ok -match "^[nN]") { Write-Log "ユーザーがキャンセル"; exit 99 }
}

if ($GuiLog) { $script:GuiLogPath = $GuiLog }

# インストール先が確定したのでログを dort にも残す
Move-LoggingTo -FinalLogDir (Join-Path $script:Dest "logs")
Write-Log "インストール先: $script:Dest / フレーバー: $($script:Flavor.id)"

# ---- ステップ2〜9 ----
Invoke-Step2-Prerequisites
Invoke-Step3-Clone
Invoke-Step4-Wheels
Invoke-Step5-Venv
Invoke-Step6-Patches
Invoke-Step7-Models
Invoke-Step8-Verify
Invoke-Step9-Finalize

# ---- 完了 (§5.10) ----
Write-Host ""
Write-Host "=============================================="
Write-Host " INSTALL OK"
Write-Host "=============================================="
foreach ($l in (Get-Msg "done_next")) { Write-Host $l }
Write-Log "INSTALL OK"
exit 0
