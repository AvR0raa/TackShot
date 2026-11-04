$ws = "C:\Users\laiki\.dsh\workspace\tackshot"
$src = Join-Path $ws "dist\TackShot"
$dst = Join-Path $ws "build\killtest2"
Remove-Item $dst -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item $src $dst -Recurse -Force

Start-Process -FilePath (Join-Path $dst "TackShot.exe") | Out-Null
Start-Sleep -Seconds 4
$procs = Get-Process -Name TackShot -ErrorAction SilentlyContinue
"running instances = " + $procs.Count
if ($procs) { $procs | ForEach-Object { "  pid=" + $_.Id + "  path=" + $_.Path } }

Remove-Item (Join-Path $ws "dist\TackShotSetup.log") -Force -ErrorAction SilentlyContinue
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = Join-Path $ws "dist\TackShotSetup.exe"
$psi.Arguments = '--silent --dir "' + $dst + '"'
$psi.UseShellExecute = $false
$p = [System.Diagnostics.Process]::Start($psi)
$null = $p.WaitForExit(300000)
"installer exit = " + $p.ExitCode

$after = Get-Process -Name TackShot -ErrorAction SilentlyContinue
"instances after = " + $after.Count
if ($after) { $after | Stop-Process -Force }

""
"=== log (grep terminated) ==="
Get-Content (Join-Path $ws "dist\TackShotSetup.log") -ErrorAction SilentlyContinue | Where-Object { $_ -match "terminat|extract finished" }
Remove-Item $dst -Recurse -Force -ErrorAction SilentlyContinue
