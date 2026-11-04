import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\setup\setup_w32.cpp"
s = io.open(p, encoding="utf-8").read()

# 1) 引入 tlhelp32
s = s.replace("#include <shlobj.h>", "#include <shlobj.h>\n#include <tlhelp32.h>")

# 2) 进程检测/结束辅助
helper = """
// 统计运行中的 TackShot.exe（限定在安装目录下）
static int CountRunningApp(const std::wstring& root, bool killThem) {
    int count = 0;
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snap == INVALID_HANDLE_VALUE) return 0;
    PROCESSENTRY32W pe{};
    pe.dwSize = sizeof(pe);
    if (Process32FirstW(snap, &pe)) {
        do {
            if (_wcsicmp(pe.szExeFile, L"TackShot.exe") != 0) continue;
            HANDLE h = OpenProcess(PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pe.th32ProcessID);
            if (!h) continue;
            wchar_t path[MAX_PATH * 2] = {};
            DWORD sz = MAX_PATH * 2;
            if (QueryFullProcessImageNameW(h, 0, path, &sz)) {
                std::wstring p(path);
                if (p.size() > root.size() && _wcsnicmp(p.c_str(), root.c_str(), root.size()) == 0) {
                    ++count;
                    if (killThem) TerminateProcess(h, 0);
                }
            }
            CloseHandle(h);
        } while (Process32NextW(snap, &pe));
    }
    CloseHandle(snap);
    return count;
}

static void RunInstall(HWND hwnd) {"""
s = s.replace("\nstatic void RunInstall(HWND hwnd) {", helper, 1)

# 3) RunInstall 里先处理运行中的进程
old = """    EnableWindow(g_btn, FALSE);
    SetWindowTextW(g_status, L"正在解压…");
    UpdateWindow(hwnd);
    std::wstring root = InstallRoot();"""
new = """    std::wstring root = InstallRoot();

    int running = CountRunningApp(root, false);
    if (running > 0) {
        std::wstring q = L"检测到 TackShot 正在运行（" + std::to_wstring(running) +
                         L" 个进程）。\\n\\n安装需要覆盖它正在使用的 DLL，必须先关闭。\\n\\n是否现在自动关闭并继续？";
        if (MessageBoxW(hwnd, q.c_str(), L"TackShot 正在运行", MB_YESNO | MB_ICONQUESTION) != IDYES) {
            SetWindowTextW(g_status, L"已取消（请先退出 TackShot）");
            return;
        }
        CountRunningApp(root, true);
        Sleep(1200);
        LogW(L"terminated %d running instance(s)", running);
    }

    EnableWindow(g_btn, FALSE);
    SetWindowTextW(g_status, L"正在解压…");
    UpdateWindow(hwnd);"""
if old in s:
    s = s.replace(old, new, 1)

# 4) 静默模式也先结束
s = s.replace("""    if (silent) {
        LogW(L"silent install begin");
        std::wstring root = InstallRoot();""",
"""    if (silent) {
        LogW(L"silent install begin");
        std::wstring root = InstallRoot();
        int runningSilent = CountRunningApp(root, false);
        if (runningSilent > 0) {
            CountRunningApp(root, true);
            Sleep(1200);
            LogW(L"silent: terminated %d running instance(s)", runningSilent);
        }""")

# 5) 写入时对 err=32（占用）做重试
old_w = """        HANDLE out = CreateFileW(target.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (out == INVALID_HANDLE_VALUE) {"""
new_w = """        HANDLE out = INVALID_HANDLE_VALUE;
        for (int attempt = 0; attempt < 8; ++attempt) {
            out = CreateFileW(target.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
            if (out != INVALID_HANDLE_VALUE) break;
            if (GetLastError() != ERROR_SHARING_VIOLATION) break;
            Sleep(300);   // 文件被占用：等一会儿重试（进程刚被杀时常见）
        }
        if (out == INVALID_HANDLE_VALUE) {"""
if old_w in s:
    s = s.replace(old_w, new_w, 1)

io.open(p, "w", encoding="utf-8").write(s)
print("installer now handles running app")
