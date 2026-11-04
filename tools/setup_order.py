import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\tools\build_setup.ps1"
s = io.open(p, encoding="utf-8").read()

pack_block = '''Write-Output "=== pack payload ==="
& $py "$ws\\tools\\pack_payload.py"
if ($LASTEXITCODE -ne 0) { exit 1 }

'''
uninst_block = '''Write-Output "=== build standalone uninstaller ==="
& g++.exe -std=c++17 -O2 -DUNICODE -D_UNICODE -DUNINSTALL_ONLY -municode -mwindows -static -static-libgcc -static-libstdc++ "$ws\\setup\\setup_w32.cpp" "$b\\setup_res.o" -o "$ws\\dist\\TackShot\\Uninstall.exe" -lcomctl32 -lole32 -luuid -lshell32 -luser32 -ladvapi32 "-Wl,-s"
if ($LASTEXITCODE -ne 0) { exit 1 }

'''
if uninst_block in s:
    s = s.replace(uninst_block, "")
    s = s.replace(pack_block, uninst_block + pack_block)
    io.open(p, "w", encoding="utf-8").write(s)
    print("order fixed: uninstaller built before packing")
else:
    print("MISS")
