$ws = "C:\Users\laiki\.dsh\workspace\tackshot"
$exe = Join-Path $ws "dist\TackShot\TackShot.exe"
Start-Process -FilePath $exe -ArgumentList @('--secret-selftest', (Join-Path $ws "build\w.txt")) -Wait -NoNewWindow | Out-Null
"=== secrets.dat 位置 ==="
@(
  (Join-Path $env:LOCALAPPDATA "TackShot\secrets.dat"),
  (Join-Path $env:APPDATA "TackShot\secrets.dat")
) | ForEach-Object { $_ + "  -> " + (Test-Path $_) }
""
"=== capture.log 位置 ==="
@(
  (Join-Path $env:LOCALAPPDATA "TackShot\capture.log"),
  (Join-Path $env:APPDATA "TackShot\capture.log")
) | ForEach-Object { $_ + "  -> " + (Test-Path $_) }
""
"=== dpi selftest ==="
$d = Join-Path $ws "build\dpi_now.txt"
Remove-Item $d -Force -ErrorAction SilentlyContinue
Start-Process -FilePath $exe -ArgumentList @('--dpi-selftest', $d) -Wait -NoNewWindow | Out-Null
Start-Sleep -Milliseconds 300
Get-Content $d -ErrorAction SilentlyContinue | Select-Object -Last 6
