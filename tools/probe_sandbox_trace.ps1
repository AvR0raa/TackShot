$ErrorActionPreference = "SilentlyContinue"
"=== 沙箱临时目录里有没有 TackShot 的痕迹 ==="
$hits = Get-ChildItem (Join-Path $env:LOCALAPPDATA "Temp") -Recurse -Filter "TackShot*.exe" -ErrorAction SilentlyContinue -Depth 4
if ($hits.Count -eq 0) { "none" } else { $hits | ForEach-Object { $_.FullName } }

""
"=== 最近的 dsh 临时目录（按时间）==="
Get-ChildItem (Join-Path $env:LOCALAPPDATA "Temp") -Directory -Filter "dsh-*" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 6 |
    ForEach-Object { $_.LastWriteTime.ToString("MM-dd HH:mm") + "  " + $_.Name }
