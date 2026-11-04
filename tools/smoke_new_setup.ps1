$ws = "C:\Users\laiki\.dsh\workspace\tackshot"
$exe = Join-Path $ws "dist\TackShotSetup.exe"
$t = Join-Path $ws "build\smoke_dir"
Remove-Item $t -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $env:TEMP "tackshot_setup_log.txt") -Force -ErrorAction SilentlyContinue

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $exe
$psi.Arguments = '--silent --dir "' + $t + '"'
$psi.UseShellExecute = $false
$p = [System.Diagnostics.Process]::Start($psi)
$null = $p.WaitForExit(180000)
"exit = " + $p.ExitCode
"files = " + (Get-ChildItem $t -Recurse -File -ErrorAction SilentlyContinue).Count
""
"=== 新日志 ==="
Get-Content (Join-Path $env:TEMP "tackshot_setup_log.txt") -ErrorAction SilentlyContinue | Select-Object -Last 6
Remove-Item $t -Recurse -Force -ErrorAction SilentlyContinue
