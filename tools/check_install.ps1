$ErrorActionPreference = "SilentlyContinue"
"=== 1) 安装器日志 ==="
$log = Join-Path $env:TEMP "tackshot_setup_log.txt"
if (Test-Path $log) { Get-Content $log -Tail 40 } else { "no log at $log" }

""
"=== 2) 注册表卸载项 ==="
$reg = Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\TackShot"
if ($reg) {
    "InstallLocation = " + $reg.InstallLocation
    "DisplayName     = " + $reg.DisplayName
} else { "no uninstall entry" }

""
"=== 3) 默认安装目录 ==="
$def = Join-Path $env:LOCALAPPDATA "Programs\TackShot"
"exists = " + (Test-Path $def)
if (Test-Path $def) { (Get-ChildItem $def -Recurse -File | Measure-Object).Count }

""
"=== 4) 快捷方式 ==="
$desk = Join-Path ([Environment]::GetFolderPath("Desktop")) "TackShot.lnk"
$menu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\TackShot\TackShot.lnk"
"desktop   = " + (Test-Path $desk) + "  " + $desk
"startmenu = " + (Test-Path $menu) + "  " + $menu
