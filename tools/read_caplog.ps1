$ErrorActionPreference = "SilentlyContinue"
$log = Join-Path $env:LOCALAPPDATA "TackShot\capture.log"
"=== capture.log ==="
if (Test-Path $log) {
    "lines = " + (Get-Content $log).Count
    Get-Content $log -Tail 12
} else { "not found" }

""
"=== installed exe ==="
$exe = Join-Path $env:LOCALAPPDATA "Programs\TackShot\TackShot.exe"
if (Test-Path $exe) {
    "mtime = " + (Get-Item $exe).LastWriteTime
    $b = [System.IO.File]::ReadAllBytes($exe)
    "size  = " + $b.Length
    "has PerMonitorV2 = " + ([System.Text.Encoding]::ASCII.GetString($b)).Contains("PerMonitorV2")
}

""
"=== config ==="
$cfg = Join-Path $env:LOCALAPPDATA "TackShot\config.json"
if (Test-Path $cfg) { Get-Content $cfg } else { "no config" }
