# steps.ps1 — インストール手順本体（INSTALLER_SPEC_v2.1.md §5）
# 全ステップは対話不要（GUI/Text の入力は setup.ps1 が先に確定させる）。
# 戻り値: 成功=$true / 失敗時は Fail-Setup で exit する。失敗コード:
#   10 事前チェック / 20 前提ソフト / 30 本体クローン / 40 ホイール
#   50 venv構築 / 60 パッチ / 70 モデル / 80 検証 / 90 最終処理

$script:TotalSteps = 9

function Fail-Setup {
    param([int]$Code, [string]$Message, [string]$HelpKey = "retry_hint")
    Write-Log "INSTALL FAILED (code=$Code) $Message" "ERROR"
    if ($HelpKey) { Write-Log ("補助メッセージ: " + (Get-Msg $HelpKey)) "HELP" }
    Write-Host ""
    Write-Host "INSTALL FAILED (code=$Code)"
    Write-Host $Message
    if ($HelpKey) { Write-Host (Get-Msg $HelpKey) }
    Write-Host "ログ: $script:LogFile"
    exit $Code
}

# ---------- ステップ1: 事前チェック (§5.0 / §4) ----------
function Invoke-Step1-Preflight {
    Write-Step 1 $script:TotalSteps "事前チェック"
    # OS: Windows 11 のみ（ビルド 22000 以上）
    $build = [System.Environment]::OSVersion.Version.Build
    if ($build -lt 22000) {
        Fail-Setup 10 "この PC の Windows は Windows 11 ではありません（ビルド $build）。Easy古典OCR v2.1 は Windows 11 のみ対応です。" $null
    }
    # アーキ（環境変数はエミュレーション環境で誤報するため Get-OSArch で実測）
    $arch = Get-OSArch
    if (($arch -ne "amd64") -and ($arch -ne "arm64")) {
        Fail-Setup 10 "対応していない CPU（$arch）です。" $null
    }
    Write-Log "OS ビルド $build / アーキ $arch"
    # インターネット接続（GitHub へ HEAD）
    $net = $false
    for ($i = 1; $i -le 3; $i++) {
        try {
            Invoke-WebRequest -Uri "https://github.com" -Method Head -UseBasicParsing -TimeoutSec 15 | Out-Null
            $net = $true; break
        } catch { Write-Log "接続確認 試行 $i 失敗: $($_.Exception.Message)" "WARN"; Start-Sleep -Seconds 3 }
    }
    if (-not $net) { Fail-Setup 10 (Get-Msg "network_proxy") $null }
    # ディスク空き（インストール先ドライブは Q1 後に再チェック。ここではシステムドライブ）
    $sysFree = Get-DriveFreeGB $env:SystemDrive
    if ($sysFree -ge 0 -and $sysFree -lt $MF.sysdisk_required_gb) {
        Fail-Setup 10 "システムドライブ（C:）の空きが ${sysFree}GB しかありません。uv キャッシュのため $($MF.sysdisk_required_gb)GB 以上必要です。ディスクの空きを確保してください。" $null
    }
    Write-Log "C: ドライブ空き ${sysFree}GB"
}

# ---------- ステップ2: 前提ソフト（git / uv） (§5.1) ----------
function Invoke-Step2-Prerequisites {
    Write-Step 2 $script:TotalSteps "前提ソフトの確認とインストール（git / uv）"
    # --- git: PATH に無ければ同梱 MinGit を展開して絶対パス使用（環境変数を変えない） ---
    $script:GitExe = $null
    $cmd = Get-Command git -ErrorAction SilentlyContinue
    if ($cmd) {
        $r = Invoke-Native "git" @("--version") -TimeoutSec 30
        if ($r.Code -eq 0) { $script:GitExe = "git"; Write-Log "システムの git を使用: $($r.Out.Trim())" }
    }
    if (-not $script:GitExe) {
        $toolsDir = Join-Path $PSScriptRoot "tools"
        $gitDir = Join-Path $toolsDir "git"
        $candidate = Join-Path $gitDir ("cmd\git.exe")
        if (Test-Path -LiteralPath $candidate) {
            $script:GitExe = $candidate
            Write-Log "キャッシュ済み MinGit を使用: $candidate"
        } else {
            Write-Log "git が見つからないため、ポータブル版 MinGit をダウンロードします（PC本体の設定は変えません）"
            $zip = Join-Path $env:TEMP "EasyKotenSetup\MinGit.zip"
            Invoke-DownloadFile -Url $MF.mingit.url -OutFile $zip -TimeoutSec 600
            New-Item -ItemType Directory -Force -Path $toolsDir | Out-Null
            $tmpX = Join-Path $toolsDir "git_extract"
            if (Test-Path -LiteralPath $tmpX) { Remove-Item -LiteralPath $tmpX -Recurse -Force }
            Expand-ZipTo -Zip $zip -Dest $tmpX
            $inner = Join-Path $tmpX $MF.mingit.inner_dir
            if (-not (Test-Path -LiteralPath $inner)) { Fail-Setup 20 "MinGit の展開に失敗しました。" }
            Move-Item -LiteralPath $inner -Destination $gitDir -Force
            Remove-Item -LiteralPath $tmpX -Recurse -Force -ErrorAction SilentlyContinue
            $script:GitExe = $candidate
            if (-not (Test-Path -LiteralPath $candidate)) { Fail-Setup 20 "MinGit の展開後に git.exe が見つかりません。" }
        }
        $r = Invoke-Native $script:GitExe @("--version") -TimeoutSec 30
        if ($r.Code -ne 0) { Fail-Setup 20 "git が正常に動作しません。" }
    }
    # --- uv: 無ければ公式スクリプトで user スコープ導入。導入経路に関係なく self update ---
    $script:UvExe = $null
    $cmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($cmd) { $script:UvExe = $cmd.Source }
    $local = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
    if (-not $script:UvExe -and (Test-Path -LiteralPath $local)) { $script:UvExe = $local }
    if (-not $script:UvExe) {
        Write-Log "uv が見つからないため公式インストールスクリプトで導入します"
        $ps1 = Join-Path $env:TEMP "EasyKotenSetup\uv-install.ps1"
        Invoke-DownloadFile -Url $MF.uv_installer_url -OutFile $ps1 -TimeoutSec 120
        $r = Invoke-Native "powershell.exe" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ps1) -TimeoutSec 600
        if ($r.Code -ne 0) { Fail-Setup 20 "uv のインストールに失敗しました。" (Get-Msg "antivirus") }
        if (-not (Test-Path -LiteralPath $local)) { Fail-Setup 20 "uv のインストール後に uv.exe が見つかりません。" }
        $script:UvExe = $local
    }
    $r = Invoke-Native $script:UvExe @("--version") -TimeoutSec 60
    Write-Log "uv: $($r.Out.Trim())"
    # lock revision 5 対策: 必ず自己更新（失敗時は警告のみ）
    Write-Log (Get-Msg "uv_old")
    $r = Invoke-Native $script:UvExe @("self", "update") -TimeoutSec 300
    if ($r.Code -ne 0) { Write-Log "uv self update は失敗しました（続行）" "WARN" }
    $r = Invoke-Native $script:UvExe @("--version") -TimeoutSec 60
    Write-Log "uv（更新後）: $($r.Out.Trim())"
}

# ---------- ステップ3: プログラム本体の取得 (§5.2) ----------
function Invoke-Step3-Clone {
    Write-Step 3 $script:TotalSteps "プログラム本体のダウンロード（git クローン）"
    $dest = $script:Dest
    $tag = $MF.tag
    if (Test-Path -LiteralPath $dest) {
        $items = @(Get-ChildItem -LiteralPath $dest -Force | Where-Object { $_.Name -ne "logs" })
        if ($items.Count -eq 0) {
            Write-Log "空フォルダーなのでそのままクローンします"
            Remove-Item -LiteralPath $dest -Force
        } elseif ((Test-Path -LiteralPath (Join-Path $dest "pyproject.toml")) -and (Test-Path -LiteralPath (Join-Path $dest "main.py"))) {
            if (Test-Path -LiteralPath (Join-Path $dest ".git")) {
                Write-Log "既存インストールを検出。更新を試みます（冪等再実行）"
                $r = Invoke-Native $script:GitExe @("-C", $dest, "fetch", "--tags", "--depth", "1", "origin") -Cwd $dest -TimeoutSec 600
                $r = Invoke-Native $script:GitExe @("-C", $dest, "checkout", "-f", $tag) -Cwd $dest -TimeoutSec 120
                if ($r.Code -ne 0) {
                    Write-Log "git による更新はできなかったため既存のファイル继续使用とします" "WARN"
                }
            } else {
                Write-Log "既存のプログラム一式を検出（git 管理外）。继续使用します" "WARN"
            }
            return
        } else {
            Fail-Setup 30 "インストール先に別の用途のファイルが入っています。空のフォルダーを選ぶか、中のファイルを移動してください: $dest" $null
        }
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
    $r = Invoke-Native $script:GitExe @("clone", "--branch", $tag, "--depth", "1", $MF.repo, $dest) -TimeoutSec 1800
    if ($r.Code -ne 0) {
        Write-Log "タグ $tag でのクローンに失敗。main ブランチを試します" "WARN"
        if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }
        $r = Invoke-Native $script:GitExe @("clone", "--depth", "1", $MF.repo, $dest) -TimeoutSec 1800
        if ($r.Code -ne 0) { Fail-Setup 30 "プログラム本体のダウンロードに失敗しました。インターネット接続を確認してください。" }
        Write-Log "警告: 最新開発版（main）でのインストールになりました。開発者の確認をお待ちください。" "WARN"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $dest "pyproject.toml"))) { Fail-Setup 30 "クローン内容が不完全です。" }
}

# ---------- ステップ4: ビルド済みホイールのダウンロード (§5.4・2026-11-22 単一zip化) ----------
# GitHub Releases の wheels-built-v<ver>.zip（約42MB、SHA256SUMS.txt 同梱）を
# リポジトリルートに展開し（zip 内は wheels/... 相対パス）、全件 SHA256 検証する。
function Invoke-Step4-Wheels {
    Write-Step 4 $script:TotalSteps "ビルド済みファイル（ホイール）のダウンロード"
    $flavor = $script:Flavor
    $zipName = $MF.wheel_archive.zip
    $dlDir = Join-Path $env:TEMP "EasyKotenSetup\dl"
    New-Item -ItemType Directory -Force -Path $dlDir | Out-Null

    $out = Join-Path $dlDir $zipName
    $downloaded = $false
    if (-not (Test-Path -LiteralPath $out)) {
        Write-Log "ホイール ZIP をダウンロード: $zipName"
        Invoke-DownloadFile -Url "$($MF.release_base)/$zipName" -OutFile $out -TimeoutSec 3600
        $downloaded = $true
    } else {
        Write-Log "キャッシュ済み ZIP を使用: $zipName"
    }
    # リポジトリルートへ展開（zip 内の wheels/... パスを保持）
    Expand-ZipTo -Zip $out -Dest $script:Dest

    # 展開された SHA256SUMS.txt で全ホイールを検証
    $sumsFile = Join-Path $script:Dest "wheels\SHA256SUMS.txt"
    if (-not (Test-Path -LiteralPath $sumsFile)) { Fail-Setup 40 "SHA256SUMS.txt が展開されませんでした（リリース資産の中身が変わった可能性があります）。" }
    $sums = @{}
    foreach ($line in (Get-Content -LiteralPath $sumsFile -Encoding UTF8)) {
        if ($line -match "^([0-9a-fA-F]{64})\s+\*?(.+)$") { $sums[$Matches[2].Trim()] = $Matches[1].ToLowerInvariant() }
    }
    $needed = @($sums.Keys | Where-Object { $_ -like "wheels/*.whl" })
    if (-not $needed) { Fail-Setup 40 "SHA256SUMS.txt にホイールがありません。" }

    $bad = @()
    foreach ($rel in $needed) {
        $f = Join-Path $script:Dest ($rel -replace "/", "\")
        if ((-not (Test-Path -LiteralPath $f)) -or ((Get-Sha256 $f) -ne $sums[$rel])) { $bad += $rel }
    }
    if ($bad) {
        if ($downloaded) {
            Fail-Setup 40 "ホイールの SHA256 が一致しません（破損またはセキュリティソフトによる改変）: $($bad -join ', ')" (Get-Msg "antivirus")
        }
        # キャッシュが古かった可能性があるので1回だけ取り直す
        Write-Log "検証失敗 $($bad.Count) 件。ZIP を取り直してもう一度確認します" "WARN"
        Remove-Item -LiteralPath $out -Force -ErrorAction SilentlyContinue
        Invoke-DownloadFile -Url "$($MF.release_base)/$zipName" -OutFile $out -TimeoutSec 3600
        Expand-ZipTo -Zip $out -Dest $script:Dest
        foreach ($rel in $needed) {
            $f = Join-Path $script:Dest ($rel -replace "/", "\")
            if (-not (Test-Path -LiteralPath $f)) { Fail-Setup 40 "ホイールが揃いません: $rel" }
            if ((Get-Sha256 $f) -ne $sums[$rel]) { Fail-Setup 40 "ホイールの SHA256 が一致しません: $rel" (Get-Msg "antivirus") }
        }
    }
    Write-Log "ホイール検証 OK（$($needed.Count) 件）"
}

# ---------- ステップ5: 実行環境構築（uv sync） (§5.5) ----------
function Invoke-Step5-Venv {
    Write-Step 5 $script:TotalSteps "Python 実行環境の構築（5〜30分かかることがあります）"
    $dest = $script:Dest
    $flavorId = $script:Flavor.id
    $venv = Join-Path $dest ("build\" + $flavorId + "\venv")
    $profileDir = Join-Path $dest ("profiles\" + $flavorId)
    if (-not (Test-Path -LiteralPath $profileDir)) { Fail-Setup 50 "フレーバー定義フォルダーがありません: $profileDir" }
    Write-Log "このステップは時間がかかります。ウィンドウを閉じずにそのままお待ちください" "NOTE"
    # UV_PROJECT_ENVIRONMENT はこのプロセス内だけで設定（恒久変更しない: §7）
    $r = Invoke-Native $script:UvExe @("sync", "--project", $profileDir) -Cwd $profileDir `
        -Env @{ "UV_PROJECT_ENVIRONMENT" = $venv } -TimeoutSec 5400
    if ($r.Code -ne 0) {
        if ($r.Out -match "Compiling|Building|failed to build") {
            Fail-Setup 50 "ビルドが必要な状態になりました（本来は発生しません）。CPU/GPU の設定を選び直して再実行するか、開発者にご連絡ください。" $null
        }
        Fail-Setup 50 "実行環境の構築に失敗しました。セキュリティソフトが一時ファイルを消した可能性があります。" (Get-Msg "antivirus")
    }
    $py = Join-Path $venv "Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $py)) { Fail-Setup 50 "仮想環境の Python が見つかりません: $py" }
    $script:VenvPy = $py
    Write-Log "仮想環境: $venv"
}

# ---------- ステップ6: venv パッチ (§5.6) ----------
function Invoke-Step6-Patches {
    Write-Step 6 $script:TotalSteps "実行環境へのパッチ当て"
    $r = Invoke-Native $script:VenvPy @("tools\apply_venv_patches.py") -Cwd $script:Dest -TimeoutSec 300
    if ($r.Code -ne 0) { Fail-Setup 60 "パッチの適用に失敗しました。開発者にご連絡ください。" }
}

# ---------- ステップ7: 学習済みモデルのダウンロード (§5.7) ----------
function Invoke-Step7-Models {
    Write-Step 7 $script:TotalSteps "学習済みモデルのダウンロード（数GB・回線により30分以上）"
    $manifestPath = Join-Path $PSScriptRoot "manifest.json"
    $installerPy = Join-Path $PSScriptRoot "installer.py"
    $r = Invoke-Native $script:VenvPy @("`"$installerPy`"", "`"$manifestPath`"", "`"$script:Dest`"") -Cwd $script:Dest -TimeoutSec 21600
    if ($r.Code -ne 0) { Fail-Setup 70 "モデルのダウンロードに失敗しました。時間をおいて再実行すると続きから再開できます。" }
}

# ---------- ステップ8: 動作検証（3層ゲート） (§5.8) ----------
function Invoke-Step8-Verify {
    Write-Step 8 $script:TotalSteps "動作検証"
    # ゲート1: パッチ状態
    $r = Invoke-Native $script:VenvPy @("tools\apply_venv_patches.py") -Cwd $script:Dest -TimeoutSec 300
    if ($r.Code -ne 0) { Fail-Setup 80 "検証1（環境パッチ）に失敗しました。再実行してください。" }
    # ゲート2: 依存パッケージとモデルファイル
    $r = Invoke-Native $script:VenvPy @("scripts\verify_env.py", "--flavor", $script:Flavor.id) -Cwd $script:Dest -TimeoutSec 600
    if ($r.Code -ne 0) { Fail-Setup 80 "検証2（実行環境の確認）に失敗しました。ログを開発者にご連絡ください。" }
    # ゲート3: スモーク OCR（manifest の smoke_image が設定されるまでスキップ）
    if ($MF.smoke_image) {
        $img = Join-Path $script:Dest ($MF.smoke_image -replace "/", "\")
        if (Test-Path -LiteralPath $img) {
            $outDir = Join-Path $env:TEMP "EasyKotenSetup\smoke"
            New-Item -ItemType Directory -Force -Path $outDir | Out-Null
            $r = Invoke-Native $script:VenvPy @("main.py", "`"$img`"", "`"$outDir`"", "--flavor", $script:Flavor.id) -Cwd $script:Dest -TimeoutSec 900
            if ($r.Code -ne 0) { Fail-Setup 80 "検証3（サンプル画像での OCR 試走）に失敗しました。" }
            Write-Log "スモーク OCR OK"
        } else {
            Write-Log "サンプル画像なし（ゲート3スキップ）" "WARN"
            Write-Log (Get-Msg "smoke_skipped")
        }
    } else {
        Write-Log (Get-Msg "smoke_skipped")
    }
}

# ---------- ステップ9: 最終処理 (§5.9) ----------
function Invoke-Step9-Finalize {
    Write-Step 9 $script:TotalSteps "最後の設定"
    # 入力フォルダー（start_ocr.bat の既定 c:/ocr/in）
    foreach ($d in @($MF.input_folder, "c:/ocr/out")) {
        try {
            New-Item -ItemType Directory -Force -Path $d | Out-Null
        } catch { Write-Log "フォルダー $d を作れませんでした（手動で作成してください）" "WARN" }
    }
    # デスクトップショートカット
    try {
        $desktop = [Environment]::GetFolderPath("Desktop")
        $ws = New-Object -ComObject WScript.Shell
        $lnk = $ws.CreateShortcut((Join-Path $desktop "Easy古典OCR.lnk"))
        $lnk.TargetPath = (Join-Path $script:Dest "start_ocr.bat")
        $lnk.WorkingDirectory = $script:Dest
        $lnk.Description = "Easy古典OCR（起動するたびにインストールフォルダー内の config.yml を読み直します）"
        $lnk.Save()
        Write-Log "デスクトップに「Easy古典OCR」のショートカットを作成しました"
    } catch {
        Write-Log "ショートカットを作れませんでした。代わりにインストール先の start_ocr.bat をダブルクリックしてください" "WARN"
        Write-Host "【重要】デスクトップにショートカットを作れませんでした。インストールフォルダーの「start_ocr.bat」をダブルクリックしてください"
    }
    # 再構築用メモ
    $env_txt = Join-Path $script:Dest "SETUP-ENV.txt"
    ("flavor=" + $script:Flavor.id + "`r`n" +
     "installed_at=" + (Get-Date -Format "s") + "`r`n" +
     "setup_version=" + $MF.version + "`r`n" +
     "uv=" + $script:UvExe + "`r`n" +
     "git=" + $script:GitExe + "`r`n" +
     "venv=build\" + $script:Flavor.id + "\venv") | Set-Content -LiteralPath $env_txt -Encoding UTF8
}
