$ErrorActionPreference = "Continue"
$ws = 'C:\Users\laiki\.dsh\workspace\tackshot'
$tc = "$ws\toolchain"
$b = "$ws\build"
$env:PATH = "C:\Python314;$tc\Tools\mingw1310_64\bin;$tc\bin;C:\Windows\System32;C:\Windows"
$py = "C:\Python314\python.exe"

Write-Output "=== windres ==="
& windres.exe -I "$ws\res" -i "$ws\res\app.rc" -o "$b\setup_res.o"
if ($LASTEXITCODE -ne 0) { Write-Output "WINDRES FAILED"; exit 1 }

Write-Output "=== build standalone uninstaller ==="
& g++.exe -std=c++17 -O2 -DUNICODE -D_UNICODE -DUNINSTALL_ONLY -municode -mwindows -static -static-libgcc -static-libstdc++ "$ws\setup\setup_w32.cpp" "$b\setup_res.o" -o "$ws\dist\TackShot\Uninstall.exe" -lcomctl32 -lole32 -luuid -lshell32 -luser32 -ladvapi32 "-Wl,-s"
if ($LASTEXITCODE -ne 0) { Write-Output "UNINSTALLER FAILED"; exit 1 }

Write-Output "=== pack payload ==="
& $py "$ws\tools\pack_payload.py"
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Output "=== compile stub ==="
& g++.exe -std=c++17 -O2 -DUNICODE -D_UNICODE -municode -mwindows -static -static-libgcc -static-libstdc++ "$ws\setup\setup_w32.cpp" "$b\setup_res.o" -o "$b\TackShotSetup.exe" -lcomctl32 -lole32 -luuid -lshell32 -luser32 -ladvapi32 "-Wl,-s"
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Output "=== append payload ==="
& $py "$ws\tools\append_payload2.py"
if ($LASTEXITCODE -ne 0) { exit 1 }
Get-Item "$ws\dist\TackShotSetup.exe" | Select-Object Name, @{n="MB";e={[math]::Round($_.Length/1MB,2)}} | Format-List
