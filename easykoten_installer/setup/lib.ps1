# lib.ps1 — Easy古典OCR セットアップ共通ヘルパー（GUI 非依存・PS 5.1 互換）
# 仕様: C:\hermes_works\easykotenocr_installer\INSTALLER_SPEC_v2.1.md §6（PowerShell 5.1 / 非対話可・リポジトリ外）

$script:LogFile = $null       # install.log（最終的にインストール先 logs へ移す）
$script:TempLogDir = $null
$script:GuiLogPath = $null    # GUI 子プロセスモード時に追記するテールログ

function Initialize-Logging {
    param([string]$TempLogDir, [string]$FinalLogDir = $null)
    $script:TempLogDir = $TempLogDir
    New-Item -ItemType Directory -Force -Path $TempLogDir | Out-Null
    $script:LogFile = Join-Path $TempLogDir "install.log"
    if ($FinalLogDir) { Move-LoggingTo -FinalLogDir $FinalLogDir }
}

function Move-LoggingTo {
    param([string]$FinalLogDir)
    New-Item -ItemType Directory -Force -Path $FinalLogDir | Out-Null
    $new = Join-Path $FinalLogDir ("install-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
    if ($script:LogFile -and (Test-Path $script:LogFile)) {
        Copy-Item -LiteralPath $script:LogFile -Destination $new -Force
    }
    $script:LogFile = $new
}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $line = "[{0}] [{1}] {2}" -f (Get-Date -Format "HH:mm:ss"), $Level, $Message
    Add-Content -LiteralPath $script:LogFile -Value $line -Encoding UTF8
    if ($script:GuiLogPath) {
        Add-Content -LiteralPath $script:GuiLogPath -Value $line -Encoding UTF8
    }
    Write-Host $line
}

# GUI 進捗行（setup-gui.ps1 が "###PROGRESS n/total" を解析）
function Write-Step {
    param([int]$N, [int]$Total, [string]$Message)
    Write-Host ("###PROGRESS {0}/{1}" -f $N, $Total)
    if ($script:GuiLogPath) {
        Add-Content -LiteralPath $script:GuiLogPath -Value ("###PROGRESS {0}/{1}" -f $N, $Total) -Encoding UTF8
    }
    Write-Log ("[{0}/{1}] {2}" -f $N, $Total, $Message)
}

function Get-Msg {
    param([string]$Key)
    if (-not $script:Messages) {
        $p = Join-Path $PSScriptRoot "messages_ja.json"
        $script:Messages = (Get-Content -LiteralPath $p -Raw -Encoding UTF8) | ConvertFrom-Json
    }
    $v = $script:Messages.$Key
    if ($null -eq $v) { return $Key }
    return $v
}

# 子プロセス実行（キャプチャ・UTF-8・環境変数上書き・タイムアウト）
# 戻り値: @{ Code=int; Out=string }
function Invoke-Native {
    param(
        [string]$Exe,
        [string[]]$ArgList = @(),
        [string]$Cwd = $null,
        [hashtable]$Env = @{},
        [int]$TimeoutSec = 1800
    )
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Exe
    $psi.Arguments = ($ArgList | ForEach-Object {
        if ($_ -match '[ "\n]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ }
    }) -join ' '
    if ($Cwd) { $psi.WorkingDirectory = $Cwd }
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $psi.StandardOutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $psi.StandardErrorEncoding = New-Object System.Text.UTF8Encoding($false)
    $psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"   # §6.1 文字化け対策
    $psi.EnvironmentVariables["PYTHONUTF8"] = "1"
    foreach ($k in $Env.Keys) { $psi.EnvironmentVariables[$k] = [string]$Env[$k] }

    Write-Log ("> " + $Exe + " " + ($ArgList -join " ")) "CMD"
    $p = [System.Diagnostics.Process]::Start($psi)
    $outTask = $p.StandardOutput.ReadToEndAsync()
    $errTask = $p.StandardError.ReadToEndAsync()
    if (-not $p.WaitForExit($TimeoutSec * 1000)) {
        try { $p.Kill($true) } catch { try { $p.Kill() } catch { } }
        throw "タイムアウト（${TimeoutSec}秒）: $Exe"
    }
    $p.WaitForExit()  # 出力フラッシュ待ち
    $combined = $outTask.Result
    if ($errTask.Result) { $combined += "`n" + $errTask.Result }
    foreach ($l in ($combined -split "`r?`n")) {
        if ($l.Trim()) { Write-Log ("  | " + $l) "OUT" }
    }
    return @{ Code = $p.ExitCode; Out = $combined }
}

# ダウンロード（リトライ3回・指数バックオフ）。Resume が必要なのは installer.py 側（モデル）
function Invoke-DownloadFile {
    param([string]$Url, [string]$OutFile, [int]$Tries = 3, [int]$TimeoutSec = 600)
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutFile) | Out-Null
    $last = $null
    for ($i = 1; $i -le $Tries; $i++) {
        try {
            Write-Log "DL $Url (試行 $i/$Tries)" "NET"
            $ProgressPreference = "SilentlyContinue"
            Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing -TimeoutSec $TimeoutSec
            $fi = Get-Item -LiteralPath $OutFile
            if ($fi.Length -lt 100) { throw "ダウンロード結果が異常に小さい（$($fi.Length) バイト）" }
            return
        } catch {
            $last = $_
            Write-Log "  失敗: $($_.Exception.Message)" "WARN"
            if ($i -lt $Tries) { Start-Sleep -Seconds (5 * $i) }
        }
    }
    throw "ダウンロード失敗: $Url / $($_.Exception.Message) / 最終: $($last.Exception.Message)"
}

function Get-Sha256 {
    param([string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Expand-ZipTo {
    param([string]$Zip, [string]$Dest)
    # tar.exe 回避: Expand-Archive のみ使用（§2.2 決定）
    Expand-Archive -LiteralPath $Zip -DestinationPath $Dest -Force
}

# OS アーキ判定（実測の落とし穴: エミュレーションされた x64 プロセスの子だと
# PROCESSOR_ARCHITECTURE 環境変数が親から継承され ARM64 でも "AMD64" と誤報する。
# 実機 Win11 ARM64 で再現済み → WMI の実値を優先し、環境変数はフォールバック）
function Get-OSArch {
    if ($script:OSArchCache) { return $script:OSArchCache }
    $arch = ""
    try {
        $osi = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
        if ($osi.OSArchitecture -match "ARM") { $arch = "arm64" } else { $arch = "amd64" }
    } catch { }
    if (-not $arch) {
        $arch = "amd64"
        if (($env:PROCESSOR_ARCHITECTURE -eq "ARM64") -or ($env:PROCESSOR_ARCHITEW6432 -eq "ARM64")) { $arch = "arm64" }
    }
    $script:OSArchCache = $arch
    return $arch
}

# HW 自動判定（start_ocr.bat と同じ思想: nvidia-smi の成败 + OS アーキ）
function Get-AutoFlavor {
    param($Flavors)
    $arch = Get-OSArch
    $gpu = $false
    try {
        $r = & nvidia-smi --query-gpu=name --format=csv,noheader 2>$null
        if (($LASTEXITCODE -eq 0) -and ($r | Out-String).Trim()) { $gpu = $true }
    } catch { $gpu = $false }
    foreach ($f in $Flavors) {
        if ($f.arch -eq $arch -and [bool]$f.gpu -eq $gpu) { return $f }
    }
    # GPU あるのに該当がなければ CPU 版へ（安全側）
    foreach ($f in $Flavors) { if ($f.arch -eq $arch -and -not [bool]$f.gpu) { return $f } }
    return $Flavors[0]
}

function Get-DriveFreeGB {
    param([string]$Path)
    $root = ([System.IO.Path]::GetPathRoot($Path))
    if (-not $root) { $root = $env:SystemDrive + "\" }
    try {
        $d = New-Object System.IO.DriveInfo($root)
        return [math]::Round($d.AvailableFreeSpace / 1GB, 1)
    } catch { return -1 }
}
