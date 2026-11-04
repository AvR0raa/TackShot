$ws = "C:\Users\laiki\.dsh\workspace\tackshot"
$src = Join-Path $ws "dist\TackShot"
$dst = Join-Path $ws "build\killtest"
Remove-Item $dst -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item $src $dst -Recurse -Force

# 启动一个占用 DLL 的实例
$app = Start-Process -FilePath (Join-Path $dst "TackShot.exe") -PassThru
Start-Sleep -Seconds 3
"app running = " + (-not $app.HasExited) + "  pid=" + $app.Id

Remove-Item (Join-Path $ws "dist\TackShotSetup.log") -Force -ErrorAction SilentlyContinue

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = Join-Path $ws "dist\TackShotSetup.exe"
$psi.Arguments = '--silent --dir "' + $dst + '"'
$psi.UseShellExecute = $false
$p = [System.Diagnostics.Process]::Start($psi)
$null = $p.WaitForExit(240000)
"installer exit = " + $p.ExitCode

"app still alive = " + (-not $app.HasExited)
if (-not $app.HasExited) { Stop-Process -Id $app.Id -Force }

""
"=== log ==="
Get-Content (Join-Path $ws "dist\TackShotSetup.log") -ErrorAction SilentlyContinue | Select-Object -Last 8

""
"=== 装后文件数（应为 32）==="
(Get-ChildItem $dst -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count

Remove-Item $dst -Recurse -Force -ErrorAction SilentlyContinue
