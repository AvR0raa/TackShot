import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\setup\setup_w32.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("static HWND g_pathEdit = nullptr;\nstatic std::wstring g_firstFailPath;\nstatic DWORD g_firstFailErr = 0;",
              "static HWND g_pathEdit = nullptr;")
s = s.replace("static std::wstring g_self;\n",
              "static std::wstring g_self;\nstatic std::wstring g_firstFailPath;\nstatic DWORD g_firstFailErr = 0;\n", 1)
io.open(p, "w", encoding="utf-8").write(s)
print("globals moved")
