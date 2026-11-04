$ErrorActionPreference = "SilentlyContinue"

"=== 1) installer log (dist/TackShotSetup.log) ==="
$log = "C:\Users\laiki\.dsh\workspace\tackshot\dist\TackShotSetup.log"
if (Test-Path $log) {
    $lines = Get-Content $log
    "lines = " + $lines.Count
    "--- last 15 ---"
    $lines | Select-Object -Last 15
    ""
    "--- GUI runs (silent=0) ---"
    $gui = $lines | Where-Object { $_ -match "silent=0" }
    if ($gui) { $gui } else { "none" }
} else {
    "log file does not exist yet"
}

""
"=== 2) registry ==="
$reg = Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\TackShot"
if ($reg) {
    "DisplayName     = " + $reg.DisplayName
    "InstallLocation = " + $reg.InstallLocation
} else { "no uninstall entry" }

""
"=== 3) default dir ==="
$def = Join-Path $env:LOCALAPPDATA "Programs\TackShot"
"exists = " + (Test-Path $def)
if (Test-Path $def) { "files = " + (Get-ChildItem $def -Recurse -File | Measure-Object).Count }

""
"=== 4) shortcuts ==="
$desk = Join-Path ([Environment]::GetFolderPath("Desktop")) "TackShot.lnk"
$menu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\TackShot\TackShot.lnk"
"desktop   = " + (Test-Path $desk)
"startmenu = " + (Test-Path $menu)

""
"=== 5) process ==="
$ps = Get-Process -Name TackShot
if ($ps) { "running count = " + $ps.Count } else { "not running" }
