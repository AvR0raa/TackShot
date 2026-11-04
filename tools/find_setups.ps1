$ErrorActionPreference = "SilentlyContinue"
$roots = @()
$roots += [Environment]::GetFolderPath("Desktop")
$roots += (Join-Path $env:USERPROFILE "Downloads")
$roots += (Join-Path $env:USERPROFILE "Documents")
$roots += $env:LOCALAPPDATA
$roots += $env:TEMP

$hits = @()
foreach ($r in $roots) {
    if (Test-Path $r) {
        $hits += Get-ChildItem $r -Recurse -File -Filter "*ackShot*.exe" -ErrorAction SilentlyContinue -Depth 3
    }
}
"=== 其它位置的 TackShot exe ==="
if ($hits.Count -eq 0) {
    "none"
} else {
    $hits | Sort-Object LastWriteTime -Descending | Select-Object -First 20 | ForEach-Object {
        $mb = [math]::Round($_.Length / 1MB, 1)
        $t = $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm")
        $t + "  " + $mb + " MB  " + $_.FullName
    }
}
""
"=== 现在时间 ==="
(Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
""
"=== dist ==="
Get-ChildItem "C:\Users\laiki\.dsh\workspace\tackshot\dist" -File | ForEach-Object {
    $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm") + "  " + [math]::Round($_.Length/1MB,1) + " MB  " + $_.Name
}
