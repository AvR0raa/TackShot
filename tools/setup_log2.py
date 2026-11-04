import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\setup\setup_w32.cpp"
s = io.open(p, encoding="utf-8").read()

# 1) 启动即记录时间与自身路径
old = """int WINAPI wWinMain(HINSTANCE hInst, HINSTANCE, PWSTR, int) {
    INITCOMMONCONTROLSEX icc{ sizeof(icc), ICC_PROGRESS_CLASS | ICC_STANDARD_CLASSES };
    InitCommonControlsEx(&icc);
    g_self.resize(32768);
    DWORD n = GetModuleFileNameW(nullptr, &g_self[0], 32768);
    g_self.resize(n);"""
new = """int WINAPI wWinMain(HINSTANCE hInst, HINSTANCE, PWSTR, int) {
    INITCOMMONCONTROLSEX icc{ sizeof(icc), ICC_PROGRESS_CLASS | ICC_STANDARD_CLASSES };
    InitCommonControlsEx(&icc);
    g_self.resize(32768);
    DWORD n = GetModuleFileNameW(nullptr, &g_self[0], 32768);
    g_self.resize(n);

    SYSTEMTIME st{};
    GetLocalTime(&st);
    LogW(L"===== launch %04d-%02d-%02d %02d:%02d:%02d  exe=%ls",
         st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond, g_self.c_str());"""
if old in s:
    s = s.replace(old, new, 1)

# 2) 解压失败要返回 false
s = s.replace("""        HANDLE out = CreateFileW(target.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (out == INVALID_HANDLE_VALUE && i < 3)
            LogW(L"create failed err=%lu target=%ls", GetLastError(), target.c_str());
        if (out != INVALID_HANDLE_VALUE) {
            DWORD wrote = 0;
            WriteFile(out, buf.data(), got, &wrote, nullptr);
            CloseHandle(out);
        }""",
"""        HANDLE out = CreateFileW(target.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (out == INVALID_HANDLE_VALUE) {
            LogW(L"create failed err=%lu target=%ls", GetLastError(), target.c_str());
            ++failedWrites;
        } else {
            DWORD wrote = 0;
            WriteFile(out, buf.data(), got, &wrote, nullptr);
            CloseHandle(out);
            if (wrote != got) {
                LogW(L"short write target=%ls want=%lu got=%lu", target.c_str(), got, wrote);
                ++failedWrites;
            }
        }""")

s = s.replace("""    LogW(L"extract to=%ls count=%lu dataStart=%lu", destRoot.c_str(), count, dataStart);
    std::vector<char> buf;
    DWORD done = 0;""",
"""    LogW(L"extract to=%ls count=%lu dataStart=%lu", destRoot.c_str(), count, dataStart);
    std::vector<char> buf;
    DWORD done = 0;
    DWORD failedWrites = 0;""")

s = s.replace("""    CloseHandle(h);
    return true;
}

static bool CreateLink""",
"""    CloseHandle(h);
    LogW(L"extract finished ok=%lu failed=%lu", count, failedWrites);
    return failedWrites == 0;
}

static bool CreateLink""")

# 3) 快捷方式/注册表结果写日志
s = s.replace("""    EnsureDir(ProgramsDir() + L"\\\\x");
    CreateLink(DesktopDir() + L"\\\\TackShot.lnk", root + L"\\\\TackShot.exe", root);
    CreateLink(ProgramsDir() + L"\\\\TackShot.lnk", root + L"\\\\TackShot.exe", root);""",
"""    EnsureDir(ProgramsDir() + L"\\\\x");
    bool l1 = CreateLink(DesktopDir() + L"\\\\TackShot.lnk", root + L"\\\\TackShot.exe", root);
    bool l2 = CreateLink(ProgramsDir() + L"\\\\TackShot.lnk", root + L"\\\\TackShot.exe", root);
    LogW(L"shortcuts desktop=%d startmenu=%d", int(l1), int(l2));""")

io.open(p, "w", encoding="utf-8").write(s)
print("logging hardened")
