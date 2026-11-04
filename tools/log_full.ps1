$ErrorActionPreference = "SilentlyContinue"
$log = Join-Path $env:TEMP "tackshot_setup_log.txt"
if (-not (Test-Path $log)) { "no log"; exit }
$all = Get-Content $log
"总行数 = " + $all.Count
""
"=== 含 silent=0 或 install dir 的行（GUI 安装痕迹）==="
$all | Where-Object { $_ -match "silent=0" -or $_ -match "install dir" } | ForEach-Object { $_ }
""
"=== 所有 start 行 ==="
$all | Where-Object { $_ -match "^start " } | ForEach-Object { $_ }
""
"=== 所有 extract to 行 ==="
$all | Where-Object { $_ -match "^extract to=" -or $_ -match "extract done" } | ForEach-Object { $_ }
