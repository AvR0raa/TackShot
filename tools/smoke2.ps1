$ws = "C:\Users\laiki\.dsh\workspace\tackshot"
$exe = Join-Path $ws "dist\TackShotSetup.exe"
$logNext = Join-Path $ws "dist\TackShotSetup.log"
Remove-Item $logNext -Force -ErrorAction SilentlyContinue

$t = Join-Path $ws "build\smoke2"
Remove-Item $t -Recurse -Force -ErrorAction SilentlyContinue
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $exe
$psi.Arguments = '--silent --dir "' + $t + '"'
$psi.UseShellExecute = $false
$p = [System.Diagnostics.Process]::Start($psi)
$null = $p.WaitForExit(180000)
"exit = " + $p.ExitCode
"files = " + (Get-ChildItem $t -Recurse -File -ErrorAction SilentlyContinue).Count
""
"=== 安装器同目录日志（新增）==="
if (Test-Path $logNext) { Get-Content $logNext -Tail 8 } else { "（没写出来）" }
Remove-Item $t -Recurse -Force -ErrorAction SilentlyContinue
