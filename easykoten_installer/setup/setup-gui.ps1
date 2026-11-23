# setup-gui.ps1 — Easy古典OCR セットアップ GUI 外殻（INSTALLER_SPEC_v2.1.md §6.1）
# 方針: GUI は入力収集と進捗表示のみ。処理本体は setup.ps1 -Mode Batch を
#       子プロセスとして起動し、テールログ（UTF-8）を 500ms ポーリングで表示する。
#       WinForms が使えない環境（制約言語モード等）ではテキストモードへ自動フォールバック。
$ErrorActionPreference = "Stop"
$PSex = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$setupPs1 = Join-Path $PSScriptRoot "setup.ps1"

function Start-TextFallback {
    Write-Host "GUI を起動できないため、テキストモードでセットアップします。"
    & $PSex -NoProfile -ExecutionPolicy Bypass -File $setupPs1
    exit $LASTEXITCODE
}

# ---- WinForms 可用性チェック（Add-Type 不可環境対策） ----
try {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
} catch {
    Start-TextFallback
}

# 高DPI（Per-Monitor V2）。PS5.1 では SetHighDpiMode が無く、shcore 版は -2 を拒否するため
# user32 の SetProcessDpiAwarenessContext を使う（実測で成功を確認済み・§6.1）
try {
    Add-Type -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool SetProcessDpiAwarenessContext(System.IntPtr value);
'@ -Name DpiUtil -Namespace Native
    [Native.DpiUtil]::SetProcessDpiAwarenessContext([System.IntPtr](-4)) | Out-Null
} catch { }

$MF = (Get-Content -LiteralPath (Join-Path $PSScriptRoot "manifest.json") -Raw -Encoding UTF8) | ConvertFrom-Json

# フレーバー自動判定（★推奨）: lib.ps1 の関数を使う
. (Join-Path $PSScriptRoot "lib.ps1")
Initialize-Logging -TempLogDir (Join-Path $env:TEMP "EasyKotenSetup")
$auto = Get-AutoFlavor $MF.flavors

# ---- フォーム ----
$form = New-Object System.Windows.Forms.Form
$form.Text = "Easy古典OCR セットアップ v$($MF.version)"
$form.Size = New-Object System.Drawing.Size(640, 560)
$form.StartPosition = "CenterScreen"
$form.Topmost = $true

$lblTitle = New-Object System.Windows.Forms.Label
$lblTitle.Text = "Easy古典OCR をインストールします"
$lblTitle.Font = New-Object System.Drawing.Font("Meiryo UI", 12, [System.Drawing.FontStyle]::Bold)
$lblTitle.Location = New-Object System.Drawing.Point(20, 15)
$lblTitle.AutoSize = $true
$form.Controls.Add($lblTitle)

$lblDest = New-Object System.Windows.Forms.Label
$lblDest.Text = "インストール先（そのまま変更しなくて構いません）"
$lblDest.Location = New-Object System.Drawing.Point(20, 55)
$lblDest.AutoSize = $true
$lblDest.Font = New-Object System.Drawing.Font("Meiryo UI", 9)
$form.Controls.Add($lblDest)

$txtDest = New-Object System.Windows.Forms.TextBox
$txtDest.Text = "C:\easykotenocr"
$txtDest.Location = New-Object System.Drawing.Point(20, 80)
$txtDest.Size = New-Object System.Drawing.Size(480, 28)
$txtDest.Font = New-Object System.Drawing.Font("Meiryo UI", 10)
$form.Controls.Add($txtDest)

$btnBrowse = New-Object System.Windows.Forms.Button
$btnBrowse.Text = "参照..."
$btnBrowse.Location = New-Object System.Drawing.Point(510, 78)
$btnBrowse.Size = New-Object System.Drawing.Size(100, 30)
$form.Controls.Add($btnBrowse)
$btnBrowse.Add_Click({
    $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
    $dlg.Description = "インストール先のフォルダーを選んでください"
    if ($dlg.ShowDialog($form) -eq "OK") { $txtDest.Text = $dlg.SelectedPath }
})

$lblFlavor = New-Object System.Windows.Forms.Label
$lblFlavor.Text = "お使いの PC に合った環境（迷う必要はありません）"
$lblFlavor.Location = New-Object System.Drawing.Point(20, 125)
$lblFlavor.AutoSize = $true
$lblFlavor.AutoEllipsis = $true
$lblFlavor.Font = New-Object System.Drawing.Font("Meiryo UI", 9)
$form.Controls.Add($lblFlavor)

$cmbFlavor = New-Object System.Windows.Forms.ComboBox
$cmbFlavor.DropDownStyle = "DropDownList"
$cmbFlavor.Location = New-Object System.Drawing.Point(20, 150)
$cmbFlavor.Size = New-Object System.Drawing.Size(590, 28)
$cmbFlavor.Font = New-Object System.Drawing.Font("Meiryo UI", 10)
$autoIndex = 0
for ($i = 0; $i -lt $MF.flavors.Count; $i++) {
    $f = $MF.flavors[$i]
    $star = if ($f.id -eq $auto.id) { "★ " } else { "   " }
    [void]$cmbFlavor.Items.Add(("{0}{1}" -f $star, $f.caption))
    if ($f.id -eq $auto.id) { $autoIndex = $i }
}
$cmbFlavor.SelectedIndex = $autoIndex
$form.Controls.Add($cmbFlavor)

$btnStart = New-Object System.Windows.Forms.Button
$btnStart.Text = "インストール開始"
$btnStart.Location = New-Object System.Drawing.Point(20, 195)
$btnStart.Size = New-Object System.Drawing.Size(200, 44)
$btnStart.Font = New-Object System.Drawing.Font("Meiryo UI", 11, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($btnStart)

$progress = New-Object System.Windows.Forms.ProgressBar
$progress.Location = New-Object System.Drawing.Point(20, 255)
$progress.Size = New-Object System.Drawing.Size(590, 22)
$progress.Minimum = 0; $progress.Maximum = 9
$form.Controls.Add($progress)

$lblStatus = New-Object System.Windows.Forms.Label
$lblStatus.Text = "「インストール開始」を押すと自動で進みます（30〜90分）。閉じないでください。"
$lblStatus.Location = New-Object System.Drawing.Point(20, 285)
$lblStatus.Size = New-Object System.Drawing.Size(590, 20)
$lblStatus.AutoEllipsis = $true
$lblStatus.Font = New-Object System.Drawing.Font("Meiryo UI", 9)
$form.Controls.Add($lblStatus)

$listLog = New-Object System.Windows.Forms.ListBox
$listLog.Location = New-Object System.Drawing.Point(20, 312)
$listLog.Size = New-Object System.Drawing.Size(590, 175)
$listLog.HorizontalScrollbar = $true
$listLog.Font = New-Object System.Drawing.Font("Consolas", 8.25)
$form.Controls.Add($listLog)

function Add-LogLine([string]$line) {
    [void]$listLog.Items.Add($line)
    $listLog.TopIndex = $listLog.Items.Count - 1
}

# ---- 開始ボタン ----
$script:TailPath = $null
$script:TailPos = 0
$script:Child = $null
$script:ChildDone = $false

$btnStart.Add_Click({
    $dest = $txtDest.Text.Trim().Trim('"')
    if (-not [System.IO.Path]::IsPathRooted($dest)) {
        [void][System.Windows.Forms.MessageBox]::Show("インストール先を絶対パス（例: C:\easykotenocr）で指定してください。", "Easy古典OCR", "OK", "Warning")
        return
    }
    $flavor = $MF.flavors[$cmbFlavor.SelectedIndex]
    $btnStart.Enabled = $false
    $lblStatus.Text = "セットアップ中です。ウィンドウを閉じないでください（30〜90分かかることがあります）..."
    $script:TailPath = Join-Path $env:TEMP ("EasyKotenSetup\gui-tail-{0}.log" -f (Get-Date -Format "yyyyMMddHHmmss"))
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $script:TailPath) | Out-Null

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $PSex
    $psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$setupPs1`" -Mode Batch -Dest `"$dest`" -FlavorId $($flavor.id) -GuiLog `"$($script:TailPath)`""
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"
    $script:Child = [System.Diagnostics.Process]::Start($psi)
    $timer.Enabled = $true
})

# ---- テールタイマー（500ms） ----
# 終了コード: 0=成功 / 99=辞退（未開始で閉じた・実行中に中断選択）/ その他=失敗
$script:FinalRc = 99
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 500
$timer.Add_Tick({
    if ($script:TailPath -and (Test-Path -LiteralPath $script:TailPath)) {
        try {
            $fs = [System.IO.File]::Open($script:TailPath, "Open", "Read", "ReadWrite")
            if ($fs.Length -gt $script:TailPos) {
                [void]$fs.Seek($script:TailPos, "Begin")
                $sr = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::UTF8)
                while ($null -ne ($line = $sr.ReadLine())) {
                    if ($line -match "^###PROGRESS (\d+)/(\d+)") {
                        $progress.Value = [Math]::Min(9, [int]$Matches[1])
                        continue
                    }
                    Add-LogLine $line
                }
                $script:TailPos = $fs.Position
                $sr.Dispose()
            }
            $fs.Close()
        } catch { }
    }
    if ($script:Child -and $script:Child.HasExited -and -not $script:ChildDone) {
        $script:ChildDone = $true
        $timer.Enabled = $false
        $rc = $script:Child.ExitCode
        $script:FinalRc = $rc
        if ($rc -eq 0) {
            $progress.Value = 9
            $lblStatus.Text = "インストール完了です！"
            Add-LogLine ""
            Add-LogLine "インストールが正常に完了しました。"
            [void][System.Windows.Forms.MessageBox]::Show(
                ("セットアップが完了しました。`n`n" + ((Get-Msg "done_next") -join "`n") + "`n"),
                "Easy古典OCR — 完了", "OK", "Information")
        } else {
            $lblStatus.Text = "セットアップは完了できませんでした（コード $rc）。"
            [void][System.Windows.Forms.MessageBox]::Show(
                ("セットアップを完了できませんでした（コード $rc）。`n`n" + (Get-Msg "retry_hint") + "`n" + (Get-Msg "support") + "`n`nログ: " + $script:TailPath),
                "Easy古典OCR — エラー", "OK", "Error")
        }
        $form.Topmost = $false
    }
})

$form.Add_Shown({ Add-LogLine "セットアップ v$($MF.version) 開始準備完了。この PC の推奨: $($auto.caption)" })

# ---- 実行中の閉じる操作は確認する（§5 の close_warning） ----
$form.Add_FormClosing({
    if ($script:Child -and -not $script:ChildDone) {
        $r = [System.Windows.Forms.MessageBox]::Show(
            (Get-Msg "close_warning"), "セットアップ中です", "YesNo", "Warning")
        if ($r -ne [System.Windows.Forms.DialogResult]::Yes) {
            $_.Cancel = $true
            return
        }
        try { $script:Child.Kill() } catch { }
        $script:ChildDone = $true
        $timer.Enabled = $false
        $script:FinalRc = 99
    }
})

[void]$form.ShowDialog()
exit $script:FinalRc
