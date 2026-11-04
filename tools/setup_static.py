import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\tools\build_setup.ps1"
s = io.open(p, encoding="utf-8").read()
s = s.replace('& g++.exe -std=c++17 -O2 -DUNICODE -D_UNICODE -municode -mwindows "$ws\\setup\\setup_w32.cpp" "$b\\setup_res.o" -o "$b\\TackShotSetup.exe" -lcomctl32 -lole32 -luuid -lshell32 -luser32 -ladvapi32 "-Wl,-s"',
              '& g++.exe -std=c++17 -O2 -DUNICODE -D_UNICODE -municode -mwindows -static -static-libgcc -static-libstdc++ "$ws\\setup\\setup_w32.cpp" "$b\\setup_res.o" -o "$b\\TackShotSetup.exe" -lcomctl32 -lole32 -luuid -lshell32 -luser32 -ladvapi32 "-Wl,-s"')
s = s.replace('& g++.exe -std=c++17 -O2 -DUNICODE -D_UNICODE -DUNINSTALL_ONLY -municode -mwindows "$ws\\setup\\setup_w32.cpp" "$b\\setup_res.o" -o "$ws\\dist\\TackShot\\Uninstall.exe" -lcomctl32 -lole32 -luuid -lshell32 -luser32 -ladvapi32 "-Wl,-s"',
              '& g++.exe -std=c++17 -O2 -DUNICODE -D_UNICODE -DUNINSTALL_ONLY -municode -mwindows -static -static-libgcc -static-libstdc++ "$ws\\setup\\setup_w32.cpp" "$b\\setup_res.o" -o "$ws\\dist\\TackShot\\Uninstall.exe" -lcomctl32 -lole32 -luuid -lshell32 -luser32 -ladvapi32 "-Wl,-s"')
io.open(p, "w", encoding="utf-8").write(s)
print("static flags added:", s.count("-static-libstdc++"))
