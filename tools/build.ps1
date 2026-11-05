$ErrorActionPreference = "Continue"
$ws = 'C:\Users\laiki\.dsh\workspace\tackshot'
$tc = "$ws\toolchain"
$src = "$ws\src"
$b = "$ws\build"
$env:PATH = "$tc\Tools\mingw1310_64\bin;$tc\bin;C:\Windows\System32;C:\Windows"

New-Item -ItemType Directory -Force -Path $b | Out-Null
Get-ChildItem $b -Filter *.o | Remove-Item -Force -ErrorAction SilentlyContinue

# ---- 托管云代理注入：tools/proxy_local.json（不入库） -> src/proxy_embedded.inc ----
$proxyUrl = ""
$proxyFile = "$ws\tools\proxy_local.json"
if (Test-Path $proxyFile) {
  try { $proxyUrl = (Get-Content $proxyFile -Raw | ConvertFrom-Json).proxy_url } catch {}
}
$inc = "// 自动生成：build.ps1 从 tools/proxy_local.json 注入；勿手改、勿提交。`r`n" +
       "static const char kManagedProxy[] = `"$proxyUrl`";`r`n"
[IO.File]::WriteAllText("$src\proxy_embedded.inc", $inc)
if ($proxyUrl) { Write-Output "=== managed proxy: $proxyUrl ===" }
else { Write-Output "=== managed proxy: none (user-credential build) ===" }

$ort = "$ws\toolchain\ort\onnxruntime-win-x64-1.31.1"
$cxxflags = @(
  "-std=c++17", "-O2", "-fexceptions",
  "-DUNICODE", "-D_UNICODE", "-DQT_NO_DEBUG",
  "-DQT_WIDGETS_LIB", "-DQT_GUI_LIB", "-DQT_CORE_LIB", "-DQT_SVG_LIB", "-DQT_NETWORK_LIB",
  "-I$tc\include", "-I$tc\include\QtCore", "-I$tc\include\QtGui",
  "-I$tc\include\QtWidgets", "-I$tc\include\QtSvg", "-I$tc\include\QtNetwork",
  "-I$tc\mkspecs\win32-g++", "-I$src", "-I$ort\include"
)

Write-Output "=== moc ==="
foreach ($h in @("config.h", "hotkey.h", "overlay.h", "pinwindow.h", "settingsdialog.h", "sessions.h", "translate.h", "theme.h", "ocrdialog.h")) {
  $out = "$b\moc_$([IO.Path]::GetFileNameWithoutExtension($h)).cpp"
  & moc.exe "$src\$h" -o "$out"
  if ($LASTEXITCODE -ne 0) { Write-Output "MOC FAILED: $h"; exit 1 }
}

Write-Output "=== windres ==="
& windres.exe -I "$ws\res" -i "$ws\res\app.rc" -o "$b\app_res.o"
if ($LASTEXITCODE -ne 0) { Write-Output "WINDRES FAILED"; exit 1 }

Write-Output "=== compile ==="
$sources = @(Get-ChildItem "$src\*.cpp" | ForEach-Object { $_.FullName })
$sources += @(Get-ChildItem "$b\moc_*.cpp" | ForEach-Object { $_.FullName })
$objs = @("$b\app_res.o")
foreach ($f in $sources) {
  $name = [IO.Path]::GetFileNameWithoutExtension($f)
  $obj = "$b\$name.o"
  $objs += $obj
  & g++.exe @cxxflags -c "$f" -o "$obj"
  if ($LASTEXITCODE -ne 0) { Write-Output "COMPILE FAILED: $f"; exit 1 }
  Write-Output ("  ok " + $name)
}

Write-Output "=== link ==="
$linkLibs = @("-lQt6Widgets","-lQt6Gui","-lQt6Core","-lQt6Svg","-lQt6Network","-lQt6EntryPoint",
  "-ld3d11","-ldxgi","-lole32","-luuid","-lshell32","-luser32","-lgdi32","-ldwmapi","-ladvapi32",
  "-lmfplat","-lmfreadwrite","-lmfuuid","-lpropsys","-lshlwapi","-lwinmm","-lcrypt32",
  "-mwindows","-Wl,-s")
& g++.exe -o "$b\TackShot.exe" @objs -L"$tc\lib" @linkLibs
if ($LASTEXITCODE -ne 0) { Write-Output "LINK FAILED"; exit 1 }

Write-Output "=== built ==="
Get-Item "$b\TackShot.exe" | Select-Object Name, Length, LastWriteTime | Format-List