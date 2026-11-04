import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\setup\setup_w32.cpp"
s = io.open(p, encoding="utf-8").read()

# 1) LogW 同时写 exe 目录和 %TEMP%
old_log = """static void LogW(const wchar_t* fmt, ...) {
    static FILE* f = nullptr;
    if (!f) {
        wchar_t tmp[MAX_PATH];
        GetTempPathW(MAX_PATH, tmp);
        std::wstring p = std::wstring(tmp) + L"tackshot_setup_log.txt";
        f = _wfopen(p.c_str(), L"a, ccs=UTF-8");
        if (!f) return;
    }
    va_list ap; va_start(ap, fmt);
    vfwprintf(f, fmt, ap);
    va_end(ap);
    fwprintf(f, L"\\n");
    fflush(f);
}"""
new_log = """static void LogTo(const std::wstring& path, const wchar_t* text) {
    FILE* f = _wfopen(path.c_str(), L"a, ccs=UTF-8");
    if (!f) return;
    fwprintf(f, L"%ls\\n", text);
    fclose(f);
}

static void LogW(const wchar_t* fmt, ...) {
    wchar_t buf[2048];
    va_list ap; va_start(ap, fmt);
    vfwprintf(buf, fmt, ap);
    va_end(ap);
    // 1) exe 同目录（最可靠：不受 %TEMP% 重定向影响）
    if (!g_self.empty()) {
        size_t pos = g_self.find_last_of(L"\\\\");
        if (pos != std::wstring::npos)
            LogTo(g_self.substr(0, pos) + L"\\\\TackShotSetup.log", buf);
    }
    // 2) %TEMP%
    wchar_t tmp[MAX_PATH];
    if (GetTempPathW(MAX_PATH, tmp))
        LogTo(std::wstring(tmp) + L"tackshot_setup_log.txt", buf);
}"""
if old_log in s:
    s = s.replace(old_log, new_log, 1)
else:
    print("LogW MISS")

# g_self 需在 LogW 之前声明
s = s.replace("static void LogTo(", "static std::wstring g_self;\n\nstatic void LogTo(", 1)
s = s.replace("static std::wstring g_self;\nstatic std::wstring g_self;\n", "static std::wstring g_self;\n")

# 2) 记录第一个失败点
s = s.replace("static HWND g_pathEdit = nullptr;",
              "static HWND g_pathEdit = nullptr;\nstatic std::wstring g_firstFailPath;\nstatic DWORD g_firstFailErr = 0;")
s = s.replace("""        if (out == INVALID_HANDLE_VALUE) {
            LogW(L"create failed err=%lu target=%ls", GetLastError(), target.c_str());
            ++failedWrites;""",
"""        if (out == INVALID_HANDLE_VALUE) {
            DWORD e = GetLastError();
            LogW(L"create failed err=%lu target=%ls", e, target.c_str());
            if (g_firstFailPath.empty()) { g_firstFailPath = target; g_firstFailErr = e; }
            ++failedWrites;""")

# 3) 失败对话框显示细节
s = s.replace("""    if (!ok) {
        MessageBoxW(hwnd, L"安装失败：无法读取安装包载荷。", L"TackShot", MB_ICONERROR);
        EnableWindow(g_btn, TRUE);
        return;
    }""",
"""    if (!ok) {
        wchar_t msg[2048];
        if (!g_firstFailPath.empty())
            swprintf_s(msg, L"安装失败。\\n\\n写入失败的文件：\\n%s\\n\\nWin32 错误码：%lu\\n\\n"
                            L"常见原因：\\n"
                            L"1) 目标目录没有写入权限（试试换到 D:\\\\ 或桌面）\\n"
                            L"2) 从聊天窗口点开时被沙箱拦截（请用资源管理器双击运行）\\n"
                            L"3) 杀毒软件拦截\\n\\n日志：TackShotSetup.log（安装器同目录）",
                       g_firstFailPath.c_str(), g_firstFailErr);
        else
            swprintf_s(msg, L"安装失败：无法读取安装包载荷。\\n\\n日志：TackShotSetup.log（安装器同目录）");
        MessageBoxW(hwnd, msg, L"TackShot", MB_ICONERROR);
        EnableWindow(g_btn, TRUE);
        return;
    }""")
io.open(p, "w", encoding="utf-8").write(s)
print("diagnostics improved")
