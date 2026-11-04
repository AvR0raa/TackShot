$ErrorActionPreference = "SilentlyContinue"
$log = "C:\Users\laiki\.dsh\workspace\tackshot\dist\TackShotSetup.log"
"=== log: $log ==="
if (Test-Path $log) {
    $l = Get-Content $log
    "lines = " + $l.Count
    "--- last 30 ---"
    $l | Select-Object -Last 30
} else { "not found" }

""
"=== install dir state ==="
$dir = Join-Path $env:LOCALAPPDATA "Programs\TackShot"
"exists = " + (Test-Path $dir)
if (Test-Path $dir) {
    "files = " + (Get-ChildItem $dir -Recurse -File | Measure-Object).Count
    "exe mtime = " + (Get-Item (Join-Path $dir "TackShot.exe")).LastWriteTime
}
