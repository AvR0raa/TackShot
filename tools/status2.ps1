$dir = Join-Path $env:LOCALAPPDATA "Programs\TackShot"
"=== installed files ==="
$f = Get-ChildItem $dir -Recurse -File
"count = " + $f.Count + "   size = " + [math]::Round(($f | Measure-Object Length -Sum).Sum / 1MB, 1) + " MB"
""
"=== top level ==="
Get-ChildItem $dir | ForEach-Object { $_.Name }
""
"=== TackShot.exe version ==="
$exe = Join-Path $dir "TackShot.exe"
if (Test-Path $exe) {
    $vi = (Get-Item $exe).VersionInfo
    "ProductName    = " + $vi.ProductName
    "FileVersion    = " + $vi.FileVersion
    "size           = " + [math]::Round((Get-Item $exe).Length / 1KB, 0) + " KB"
} else { "missing" }
""
"=== desktop shortcut target ==="
$lnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "TackShot.lnk"
if (Test-Path $lnk) {
    $sh = New-Object -ComObject WScript.Shell
    $s = $sh.CreateShortcut($lnk)
    "target = " + $s.TargetPath
    "exists = " + (Test-Path $s.TargetPath)
}
