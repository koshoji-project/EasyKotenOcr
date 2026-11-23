# fix_bom.ps1 — installer 配下の .ps1/.bat/.json/.py/.txt に UTF-8 BOM を保証付与
# （PS5.1 が BOM なし UTF-8 の日本語を Shift-JIS と誤読する問題への恒久対策・仕様 §6.1）
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$fixed = 0; $ok = 0
Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object { $_.Extension -in ".ps1", ".bat", ".json", ".py", ".txt" } | ForEach-Object {
    $b = [System.IO.File]::ReadAllBytes($_.FullName)
    if ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF) {
        $ok++
    } else {
        # CRLF でも LF でも中身は変えない（BOM のみ足す）
        $outBytes = New-Object byte[] ($b.Length + 3)
        $outBytes[0] = 0xEF; $outBytes[1] = 0xBB; $outBytes[2] = 0xBF
        [System.Array]::Copy($b, 0, $outBytes, 3, $b.Length)
        [System.IO.File]::WriteAllBytes($_.FullName, $outBytes)
        $fixed++
        Write-Host ("BOM 付与: " + $_.FullName.Substring($root.Length + 1))
    }
}
Write-Host "BOM 済み: $ok / 今回付与: $fixed"
# .bat は念のため CRLF も保証する（set /p 等の問題回避。LF のみの bat は不安定）
Get-ChildItem -LiteralPath $root -Recurse -Filter *.bat | ForEach-Object {
    $t = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)
    $n = ($t -replace "`r`n", "`n") -replace "`n", "`r`n"
    if ($n -ne $t) {
        [System.IO.File]::WriteAllText($_.FullName, $n, (New-Object System.Text.UTF8Encoding($true)))
        Write-Host ("CRLF 正規化: " + $_.Name)
    }
}
