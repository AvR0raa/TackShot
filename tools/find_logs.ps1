$ErrorActionPreference = "SilentlyContinue"
"=== 所有 tackshot_setup_log.txt ==="
$hits = Get-ChildItem $env:LOCALAPPDATA -Recurse -File -Filter "tackshot_setup_log.txt" -ErrorAction SilentlyContinue -Depth 4
if ($hits.Count -eq 0) { "none" }
foreach ($h in $hits) {
    $h.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss") + "  " + $h.FullName + "  (" + $h.Length + " bytes)"
}
""
"=== dsh 临时目录 ==="
Get-ChildItem (Join-Path $env:LOCALAPPDATA "Temp") -Directory -Filter "dsh-*" -ErrorAction SilentlyContinue | Select-Object -First 10 | ForEach-Object { $_.Name }
