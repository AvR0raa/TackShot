// TackShot 安装程序（纯 Win32，无需 Qt 运行库）
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <commctrl.h>
#include <shellapi.h>
#include <shlobj.h>
#include <tlhelp32.h>
#include <shellapi.h>
#include <objbase.h>
#include <string>
#include <vector>
#include <cstdio>
#include <cstdarg>

#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "advapi32.lib")

static std::wstring g_self;
static std::wstring g_firstFailPath;
static DWORD g_firstFailErr = 0;

static void LogTo(const std::wstring& path, const wchar_t* text) {
    FILE* f = _wfopen(path.c_str(), L"a, ccs=UTF-8");
    if (!f) return;
    fwprintf(f, L"%ls\n", text);
    fclose(f);
}

static void LogW(const wchar_t* fmt, ...) {
    wchar_t buf[2048];
    va_list ap; va_start(ap, fmt);
    vswprintf(buf, 2048, fmt, ap);
    va_end(ap);
    // 1) exe 同目录（最可靠：不受 %TEMP% 重定向影响）
    if (!g_self.empty()) {
        size_t pos = g_self.find_last_of(L"\\");
        if (pos != std::wstring::npos)
            LogTo(g_self.substr(0, pos) + L"\\TackShotSetup.log", buf);
    }
    // 2) %TEMP%
    wchar_t tmp[MAX_PATH];
    if (GetTempPathW(MAX_PATH, tmp))
        LogTo(std::wstring(tmp) + L"tackshot_setup_log.txt", buf);
}

static const char kMagic[] = "TSPAYLD1";
static const int kFooter = 16;

struct Entry { std::wstring path; DWORD size; DWORD offset; };
static std::vector<Entry> g_entries;

static std::wstring LocalAppData() {
    wchar_t buf[MAX_PATH] = {};
    if (SUCCEEDED(SHGetFolderPathW(nullptr, CSIDL_LOCAL_APPDATA, nullptr, 0, buf)))
        return buf;
    return L"C:\\";
}

static std::wstring g_installRoot;
static bool g_testMode = false;
static std::wstring InstallRoot() {
    if (!g_installRoot.empty()) return g_installRoot;
    return LocalAppData() + L"\\Programs\\TackShot";
}

static std::wstring DesktopDir() {
    wchar_t buf[MAX_PATH] = {};
    if (SUCCEEDED(SHGetFolderPathW(nullptr, CSIDL_DESKTOPDIRECTORY, nullptr, 0, buf))) return buf;
    return L"";
}

static std::wstring ProgramsDir() {
    wchar_t buf[MAX_PATH] = {};
    if (SUCCEEDED(SHGetFolderPathW(nullptr, CSIDL_PROGRAMS, nullptr, 0, buf))) return std::wstring(buf) + L"\\TackShot";
    return L"";
}

static bool ReadSelf(std::wstring& payloadPath, DWORD& offset, DWORD& size) {
    HANDLE h = CreateFileW(g_self.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, 0, nullptr);
    if (h == INVALID_HANDLE_VALUE) return false;
    LARGE_INTEGER li{};
    GetFileSizeEx(h, &li);
    if (li.QuadPart <= kFooter) { CloseHandle(h); return false; }
    LARGE_INTEGER pos{}; pos.QuadPart = li.QuadPart - kFooter;
    SetFilePointerEx(h, pos, nullptr, FILE_BEGIN);
    char tail[kFooter] = {};
    DWORD got = 0;
    ReadFile(h, tail, kFooter, &got, nullptr);
    CloseHandle(h);
    if (got != kFooter || memcmp(tail, kMagic, 8) != 0) return false;
    memcpy(&offset, tail + 8, 4);
    memcpy(&size, tail + 12, 4);
    return true;
}

static bool LoadIndex() {
    DWORD off = 0, sz = 0;
    if (!ReadSelf(g_self, off, sz)) return false;
    HANDLE h = CreateFileW(g_self.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, 0, nullptr);
    if (h == INVALID_HANDLE_VALUE) return false;
    std::vector<char> data(sz);
    LARGE_INTEGER pos{}; pos.QuadPart = off;
    SetFilePointerEx(h, pos, nullptr, FILE_BEGIN);
    DWORD read = 0;
    ReadFile(h, data.data(), sz, &read, nullptr);
    CloseHandle(h);
    if (read != sz) return false;

    const char* p = data.data();
    DWORD count = 0;
    memcpy(&count, p, 4); p += 4;
    for (DWORD i = 0; i < count; ++i) {
        DWORD plen = 0; memcpy(&plen, p, 4); p += 4;
        std::wstring path((const wchar_t*)p, plen / 2); p += plen;
        Entry e; e.path = path;
        memcpy(&e.size, p, 4); p += 4;
        memcpy(&e.offset, p, 4); p += 4;
        g_entries.push_back(e);
    }
    return !g_entries.empty();
}

static void EnsureDir(const std::wstring& path) {
    std::wstring cur;
    for (size_t i = 0; i < path.size(); ++i) {
        cur += path[i];
        if (path[i] == L'\\' || i + 1 == path.size()) {
            if (cur.size() > 3) CreateDirectoryW(cur.c_str(), nullptr);
        }
    }
}

static bool ExtractAll(const std::wstring& destRoot, HWND progress) {
    DWORD off = 0, sz = 0;
    if (!ReadSelf(g_self, off, sz)) return false;
    HANDLE h = CreateFileW(g_self.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, 0, nullptr);
    if (h == INVALID_HANDLE_VALUE) return false;

    HANDLE hIndex = CreateFileW(g_self.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, 0, nullptr);
    std::vector<char> index(sz);
    LARGE_INTEGER pos{}; pos.QuadPart = off;
    SetFilePointerEx(hIndex, pos, nullptr, FILE_BEGIN);
    DWORD rd = 0;
    ReadFile(hIndex, index.data(), sz, &rd, nullptr);
    CloseHandle(hIndex);

    const char* p = index.data();
    DWORD count = 0; memcpy(&count, p, 4); p += 4;
    DWORD dataStart = 0;
    {
        const char* q = p;
        for (DWORD i = 0; i < count; ++i) {
            DWORD plen = 0; memcpy(&plen, q, 4); q += 4 + plen + 8;
        }
        dataStart = DWORD(q - index.data());
    }

    LogW(L"extract to=%ls count=%lu dataStart=%lu", destRoot.c_str(), count, dataStart);
    std::vector<char> buf;
    DWORD done = 0;
    DWORD failedWrites = 0;
    for (DWORD i = 0; i < count; ++i) {
        DWORD plen = 0; memcpy(&plen, p, 4); p += 4;
        std::wstring rel((const wchar_t*)p, plen / 2); p += plen;
        for (wchar_t& c : rel) if (c == L'/') c = L'\\';
        DWORD fsize = 0, foff = 0;
        memcpy(&fsize, p, 4); p += 4;
        memcpy(&foff, p, 4); p += 4;

        std::wstring target = destRoot + L"\\" + rel;
        std::wstring dir = target.substr(0, target.find_last_of(L'\\'));
        EnsureDir(dir);

        buf.resize(fsize);
        LARGE_INTEGER fp{}; fp.QuadPart = LONGLONG(off) + dataStart + foff;
        SetFilePointerEx(h, fp, nullptr, FILE_BEGIN);
        DWORD got = 0;
        ReadFile(h, buf.data(), fsize, &got, nullptr);

        HANDLE out = INVALID_HANDLE_VALUE;
        for (int attempt = 0; attempt < 8; ++attempt) {
            out = CreateFileW(target.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
            if (out != INVALID_HANDLE_VALUE) break;
            if (GetLastError() != ERROR_SHARING_VIOLATION) break;
            Sleep(300);   // 文件被占用：等一会儿重试（进程刚被杀时常见）
        }
        if (out == INVALID_HANDLE_VALUE) {
            DWORD e = GetLastError();
            LogW(L"create failed err=%lu target=%ls", e, target.c_str());
            if (g_firstFailPath.empty()) { g_firstFailPath = target; g_firstFailErr = e; }
            ++failedWrites;
        } else {
            DWORD wrote = 0;
            WriteFile(out, buf.data(), got, &wrote, nullptr);
            CloseHandle(out);
            if (wrote != got) {
                LogW(L"short write target=%ls want=%lu got=%lu", target.c_str(), got, wrote);
                ++failedWrites;
            }
        }
        ++done;
        if (progress && (i % 4 == 0 || i + 1 == count))
            SendMessageW(progress, PBM_SETPOS, (WPARAM)((done * 100) / count), 0);
    }
    CloseHandle(h);
    LogW(L"extract finished ok=%lu failed=%lu", count, failedWrites);
    return failedWrites == 0;
}

static bool CreateLink(const std::wstring& link, const std::wstring& target, const std::wstring& workDir) {
    IShellLinkW* sl = nullptr;
    if (FAILED(CoCreateInstance(CLSID_ShellLink, nullptr, CLSCTX_INPROC_SERVER, IID_IShellLinkW, (void**)&sl)))
        return false;
    sl->SetPath(target.c_str());
    sl->SetWorkingDirectory(workDir.c_str());
    sl->SetDescription(L"TackShot 截图");
    sl->SetIconLocation(target.c_str(), 0);
    IPersistFile* pf = nullptr;
    bool ok = false;
    if (SUCCEEDED(sl->QueryInterface(IID_IPersistFile, (void**)&pf))) {
        ok = SUCCEEDED(pf->Save(link.c_str(), TRUE));
        pf->Release();
    }
    sl->Release();
    return ok;
}

static void SetRegString(HKEY root, const wchar_t* sub, const wchar_t* name, const std::wstring& value) {
    HKEY k;
    if (RegCreateKeyExW(root, sub, 0, nullptr, 0, KEY_WRITE, nullptr, &k, nullptr) == ERROR_SUCCESS) {
        RegSetValueExW(k, name, 0, REG_SZ, (const BYTE*)value.c_str(),
                       DWORD((value.size() + 1) * sizeof(wchar_t)));
        RegCloseKey(k);
    }
}

static void DoUninstall() {
    std::wstring dir = InstallRoot();
    DeleteFileW((DesktopDir() + L"\\TackShot.lnk").c_str());
    DeleteFileW((ProgramsDir() + L"\\TackShot.lnk").c_str());
    RemoveDirectoryW(ProgramsDir().c_str());
    HKEY k;
    if (RegOpenKeyExW(HKEY_CURRENT_USER, L"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall", 0, KEY_ALL_ACCESS, &k) == ERROR_SUCCESS) {
        RegDeleteTreeW(k, L"TackShot");
        RegCloseKey(k);
    }
    if (RegOpenKeyExW(HKEY_CURRENT_USER, L"Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, KEY_ALL_ACCESS, &k) == ERROR_SUCCESS) {
        RegDeleteValueW(k, L"TackShot");
        RegCloseKey(k);
    }
    std::wstring cmd = L"cmd.exe /c timeout /t 1 /nobreak >nul & rmdir /s /q \"" + dir + L"\"";
    STARTUPINFOW si{ sizeof(si) };
    PROCESS_INFORMATION pi{};
    std::vector<wchar_t> buf(cmd.begin(), cmd.end()); buf.push_back(0);
    CreateProcessW(nullptr, buf.data(), nullptr, nullptr, FALSE, CREATE_NO_WINDOW, nullptr, nullptr, &si, &pi);
}

// ---------------- 安装窗口 ----------------
static HWND g_hwnd = nullptr, g_progress = nullptr, g_status = nullptr, g_btn = nullptr;
static HWND g_pathEdit = nullptr;
static HFONT g_font = nullptr;

static void SetFont(HWND h) { SendMessageW(h, WM_SETFONT, (WPARAM)g_font, TRUE); }

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

static void RunInstall(HWND hwnd) {
    if (g_pathEdit) {
        wchar_t buf[MAX_PATH * 2] = {};
        GetWindowTextW(g_pathEdit, buf, MAX_PATH * 2);
        std::wstring dir = buf;
        while (!dir.empty() && (dir.back() == L' ' || dir.back() == L'"')) dir.pop_back();
        bool looksAbsolute = (dir.find(L':') != std::wstring::npos) ||
                             (dir.size() > 2 && dir[0] == L'\\' && dir[1] == L'\\');
        if (dir.size() < 4 || !looksAbsolute) {
            MessageBoxW(hwnd, L"请先选择一个有效的安装目录。", L"TackShot", MB_ICONWARNING);
            return;
        }
        g_installRoot = dir;
        LogW(L"install dir = %ls", dir.c_str());
    }
    std::wstring root = InstallRoot();

    int running = CountRunningApp(root, false);
    if (running > 0) {
        std::wstring q = L"检测到 TackShot 正在运行（" + std::to_wstring(running) +
                         L" 个进程）。\n\n安装需要覆盖它正在使用的 DLL，必须先关闭。\n\n是否现在自动关闭并继续？";
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
    UpdateWindow(hwnd);
    EnsureDir(root);
    bool ok = ExtractAll(root, g_progress);
    if (!ok) {
        wchar_t msg[2048];
        if (!g_firstFailPath.empty())
            swprintf_s(msg, L"安装失败。\n\n写入失败的文件：\n%s\n\nWin32 错误码：%lu\n\n"
                            L"常见原因：\n"
                            L"1) 目标目录没有写入权限（试试换到 D:\\ 或桌面）\n"
                            L"2) 从聊天窗口点开时被沙箱拦截（请用资源管理器双击运行）\n"
                            L"3) 杀毒软件拦截\n\n日志：TackShotSetup.log（安装器同目录）",
                       g_firstFailPath.c_str(), g_firstFailErr);
        else
            swprintf_s(msg, L"安装失败：无法读取安装包载荷。\n\n日志：TackShotSetup.log（安装器同目录）");
        MessageBoxW(hwnd, msg, L"TackShot", MB_ICONERROR);
        EnableWindow(g_btn, TRUE);
        return;
    }
    // 复制自身为卸载程序
    CopyFileW(g_self.c_str(), (root + L"\\Uninstall.exe").c_str(), FALSE);

    EnsureDir(ProgramsDir() + L"\\x");
    bool l1 = CreateLink(DesktopDir() + L"\\TackShot.lnk", root + L"\\TackShot.exe", root);
    bool l2 = CreateLink(ProgramsDir() + L"\\TackShot.lnk", root + L"\\TackShot.exe", root);
    LogW(L"shortcuts desktop=%d startmenu=%d", int(l1), int(l2));

    const wchar_t* uninst = L"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TackShot";
    SetRegString(HKEY_CURRENT_USER, uninst, L"DisplayName", L"TackShot 图钉截图");
    SetRegString(HKEY_CURRENT_USER, uninst, L"DisplayVersion", L"1.0.0");
    SetRegString(HKEY_CURRENT_USER, uninst, L"Publisher", L"TackShot");
    SetRegString(HKEY_CURRENT_USER, uninst, L"InstallLocation", root);
    SetRegString(HKEY_CURRENT_USER, uninst, L"DisplayIcon", root + L"\\TackShot.exe");
    SetRegString(HKEY_CURRENT_USER, uninst, L"UninstallString", L"\"" + root + L"\\Uninstall.exe\" --uninstall");
    SetRegString(HKEY_CURRENT_USER, uninst, L"InstallSource", g_self);

    SetWindowTextW(g_status, L"安装完成");
    SendMessageW(g_progress, PBM_SETPOS, 100, 0);
    {
        std::wstring doneMsg = L"TackShot 安装完成。\n\n安装目录：\n" + root +
                               L"\n\n默认热键：Ctrl+Alt+A（可在设置中修改）\n\n是否立即启动？";
        if (MessageBoxW(hwnd, doneMsg.c_str(), L"TackShot", MB_YESNO | MB_ICONINFORMATION) == IDYES) {
            ShellExecuteW(nullptr, L"open", (root + L"\\TackShot.exe").c_str(), nullptr, root.c_str(), SW_SHOWNORMAL);
            DestroyWindow(hwnd);
            return;
        }
    }
    DestroyWindow(hwnd);
}

static LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
    case WM_CREATE: {
        g_font = CreateFontW(-16, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
                             OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Microsoft YaHei UI");
        HWND hTitle = CreateWindowW(L"STATIC", L"TackShot 图钉截图  1.0.0", WS_CHILD | WS_VISIBLE,
                                    24, 20, 400, 28, hwnd, nullptr, nullptr, nullptr);
        HFONT big = CreateFontW(-24, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
                                OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Microsoft YaHei UI");
        SendMessageW(hTitle, WM_SETFONT, (WPARAM)big, TRUE);

        HWND hInfo = CreateWindowW(L"STATIC", L"本地截图 / 标注 / 贴图工具（无网络依赖）", WS_CHILD | WS_VISIBLE,
                                   24, 54, 400, 22, hwnd, nullptr, nullptr, nullptr);
        SetFont(hInfo);
        HWND hPathLabel = CreateWindowW(L"STATIC", L"安装位置：", WS_CHILD | WS_VISIBLE,
                                        24, 86, 70, 22, hwnd, nullptr, nullptr, nullptr);
        SetFont(hPathLabel);
        g_pathEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", InstallRoot().c_str(),
                                     WS_CHILD | WS_VISIBLE | WS_TABSTOP | ES_AUTOHSCROLL,
                                     92, 84, 270, 24, hwnd, (HMENU)10, nullptr, nullptr);
        SetFont(g_pathEdit);
        HWND browse = CreateWindowW(L"BUTTON", L"浏览…", WS_CHILD | WS_VISIBLE,
                                    370, 84, 84, 24, hwnd, (HMENU)3, nullptr, nullptr);
        SetFont(browse);

        g_progress = CreateWindowW(PROGRESS_CLASSW, nullptr, WS_CHILD | WS_VISIBLE,
                                   24, 118, 430, 18, hwnd, nullptr, nullptr, nullptr);
        g_status = CreateWindowW(L"STATIC", L"准备就绪", WS_CHILD | WS_VISIBLE,
                                 24, 144, 430, 22, hwnd, nullptr, nullptr, nullptr);
        SetFont(g_status);

        g_btn = CreateWindowW(L"BUTTON", L"安装", WS_CHILD | WS_VISIBLE | BS_DEFPUSHBUTTON,
                              300, 190, 80, 30, hwnd, (HMENU)1, nullptr, nullptr);
        SetFont(g_btn);
        HWND cancel = CreateWindowW(L"BUTTON", L"取消", WS_CHILD | WS_VISIBLE,
                                    388, 190, 80, 30, hwnd, (HMENU)2, nullptr, nullptr);
        SetFont(cancel);
        return 0;
    }
    case WM_COMMAND:
        if (LOWORD(wp) == 1) RunInstall(hwnd);
        else if (LOWORD(wp) == 2) DestroyWindow(hwnd);
        else if (LOWORD(wp) == 3) {
            BROWSEINFOW bi{};
            bi.hwndOwner = hwnd;
            bi.lpszTitle = L"选择安装目录";
            bi.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE | BIF_USENEWUI;
            LPITEMIDLIST pidl = SHBrowseForFolderW(&bi);
            if (pidl) {
                wchar_t buf[MAX_PATH] = {};
                if (SHGetPathFromIDListW(pidl, buf)) {
                    std::wstring sel = buf;
                    if (!sel.empty() && sel.back() != L'\\') sel += L"\\";
                    sel += L"TackShot";
                    SetWindowTextW(g_pathEdit, sel.c_str());
                }
                CoTaskMemFree(pidl);
            }
        }
        return 0;
    case WM_CLOSE:
        DestroyWindow(hwnd);
        return 0;
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(hwnd, msg, wp, lp);
}

int WINAPI wWinMain(HINSTANCE hInst, HINSTANCE, PWSTR, int) {
    INITCOMMONCONTROLSEX icc{ sizeof(icc), ICC_PROGRESS_CLASS | ICC_STANDARD_CLASSES };
    InitCommonControlsEx(&icc);
    g_self.resize(32768);
    DWORD n = GetModuleFileNameW(nullptr, &g_self[0], 32768);
    g_self.resize(n);

    SYSTEMTIME st{};
    GetLocalTime(&st);
    LogW(L"===== launch %04d-%02d-%02d %02d:%02d:%02d  exe=%ls",
         st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond, g_self.c_str());

    int argc = 0;
    LPWSTR* argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    bool silent = false, uninstall = false;
    for (int i = 1; i < argc; ++i) {
        if (_wcsicmp(argv[i], L"--silent") == 0) silent = true;
        if (_wcsicmp(argv[i], L"--uninstall") == 0) uninstall = true;
        if (_wcsicmp(argv[i], L"--dir") == 0 && i + 1 < argc) { g_installRoot = argv[++i]; g_testMode = true; }
    }
#ifndef UNINSTALL_ONLY
    LogW(L"start argc=%d silent=%d uninstall=%d", argc, int(silent), int(uninstall));
    if (!LoadIndex()) {
        LogW(L"LoadIndex failed");
        MessageBoxW(nullptr, L"安装包损坏（找不到载荷）。", L"TackShot", MB_ICONERROR);
        return 1;
    }
    LogW(L"index loaded, entries=%d", int(g_entries.size()));
#else
    (void)argc;
    silent = true; uninstall = true;
#endif
    CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);

    if (uninstall) {
        if (!silent && MessageBoxW(nullptr, L"确定要卸载 TackShot 吗？", L"TackShot 卸载",
                                   MB_YESNO | MB_ICONQUESTION) != IDYES)
            return 0;
        DoUninstall();
        return 0;
    }
    if (silent) {
        LogW(L"silent install begin");
        std::wstring root = InstallRoot();
        int runningSilent = CountRunningApp(root, false);
        if (runningSilent > 0) {
            CountRunningApp(root, true);
            Sleep(1200);
            LogW(L"silent: terminated %d running instance(s)", runningSilent);
        }
        EnsureDir(root);
        if (!ExtractAll(root, nullptr)) { LogW(L"ExtractAll failed"); return 1; }
        LogW(L"extract done");
        if (g_testMode) {
            bool ok = CreateLink(root + L"\\TackShot.lnk", root + L"\\TackShot.exe", root);
            LogW(L"test mode shortcut created=%d", int(ok));
            return 0;
        }
        EnsureDir(ProgramsDir() + L"\\x");
        CreateLink(DesktopDir() + L"\\TackShot.lnk", root + L"\\TackShot.exe", root);
        CreateLink(ProgramsDir() + L"\\TackShot.lnk", root + L"\\TackShot.exe", root);
        const wchar_t* uninst = L"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TackShot";
        SetRegString(HKEY_CURRENT_USER, uninst, L"DisplayName", L"TackShot 图钉截图");
        SetRegString(HKEY_CURRENT_USER, uninst, L"DisplayVersion", L"1.0.0");
        SetRegString(HKEY_CURRENT_USER, uninst, L"Publisher", L"TackShot");
        SetRegString(HKEY_CURRENT_USER, uninst, L"InstallLocation", root);
        SetRegString(HKEY_CURRENT_USER, uninst, L"DisplayIcon", root + L"\\TackShot.exe");
        SetRegString(HKEY_CURRENT_USER, uninst, L"UninstallString", L"\"" + root + L"\\Uninstall.exe\" --uninstall");
        return 0;
    }

    WNDCLASSEXW wc{ sizeof(wc) };
    wc.style = CS_HREDRAW | CS_VREDRAW;
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInst;
    wc.hCursor = LoadCursor(nullptr, IDC_ARROW);
    wc.hbrBackground = CreateSolidBrush(RGB(250, 250, 252));
    wc.lpszClassName = L"TackShotSetupWnd";
    wc.hIcon = LoadIconW(hInst, MAKEINTRESOURCEW(1));
    RegisterClassExW(&wc);

    RECT rc{ 0, 0, 478, 240 };
    AdjustWindowRect(&rc, WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX, FALSE);
    HWND hwnd = CreateWindowExW(0, L"TackShotSetupWnd", L"TackShot 安装程序",
                                WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
                                CW_USEDEFAULT, CW_USEDEFAULT, rc.right - rc.left, rc.bottom - rc.top,
                                nullptr, nullptr, hInst, nullptr);
    ShowWindow(hwnd, SW_SHOW);
    UpdateWindow(hwnd);

    MSG msg;
    while (GetMessageW(&msg, nullptr, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
    return 0;
}
