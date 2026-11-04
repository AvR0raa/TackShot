$ErrorActionPreference = "SilentlyContinue"
"=== 找所有 tackshot_setup_log.txt（按时间倒序）==="
$hits = @()
$hits += Get-ChildItem $env:TEMP -Recurse -File -Filter "tackshot_setup_log.txt" -Depth 3 -ErrorAction SilentlyContinue
$hits += Get-ChildItem (Join-Path $env:LOCALAPPDATA "Temp") -Recurse -File -Filter "tackshot_setup_log.txt" -Depth 4 -ErrorAction SilentlyContinue
$hits = $hits | Sort-Object LastWriteTime -Descending | Select-Object -Unique
foreach ($h in $hits) {
    $h.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss") + "  " + $h.FullName + "  (" + $h.Length + "B)"
}

""
"=== 最新那份的内容（后 40 行）==="
if ($hits.Count -gt 0) {
    Get-Content $hits[0].FullName -Tail 40
} else {
    "（没有日志文件）"
}
