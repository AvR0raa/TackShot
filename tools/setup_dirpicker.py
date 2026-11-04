import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\setup\setup_w32.cpp"
s = io.open(p, encoding="utf-8").read()

# 1) 全局控件句柄
s = s.replace("static HWND g_hwnd = nullptr, g_progress = nullptr, g_status = nullptr, g_btn = nullptr;",
              "static HWND g_hwnd = nullptr, g_progress = nullptr, g_status = nullptr, g_btn = nullptr;\n"
              "static HWND g_pathEdit = nullptr;")

# 2) WM_CREATE：把静态路径改成可编辑输入框 + 浏览按钮
old_path = """        std::wstring pathText = L"安装位置：" + InstallRoot();
        HWND hPath = CreateWindowW(L"STATIC", pathText.c_str(), WS_CHILD | WS_VISIBLE | SS_PATHELLIPSIS,
                                   24, 84, 430, 22, hwnd, nullptr, nullptr, nullptr);
        SetFont(hPath);"""
new_path = """        HWND hPathLabel = CreateWindowW(L"STATIC", L"安装位置：", WS_CHILD | WS_VISIBLE,
                                        24, 86, 70, 22, hwnd, nullptr, nullptr, nullptr);
        SetFont(hPathLabel);
        g_pathEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", InstallRoot().c_str(),
                                     WS_CHILD | WS_VISIBLE | WS_TABSTOP | ES_AUTOHSCROLL,
                                     92, 84, 270, 24, hwnd, (HMENU)10, nullptr, nullptr);
        SetFont(g_pathEdit);
        HWND browse = CreateWindowW(L"BUTTON", L"浏览…", WS_CHILD | WS_VISIBLE,
                                    370, 84, 84, 24, hwnd, (HMENU)3, nullptr, nullptr);
        SetFont(browse);"""
if old_path in s:
    s = s.replace(old_path, new_path, 1)

# 3) 浏览按钮处理 + 读取输入框
old_cmd = """    case WM_COMMAND:
        if (LOWORD(wp) == 1) RunInstall(hwnd);
        else if (LOWORD(wp) == 2) DestroyWindow(hwnd);
        return 0;"""
new_cmd = """    case WM_COMMAND:
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
                    if (!sel.empty() && sel.back() != L'\\\\') sel += L"\\\\";
                    sel += L"TackShot";
                    SetWindowTextW(g_pathEdit, sel.c_str());
                }
                CoTaskMemFree(pidl);
            }
        }
        return 0;"""
if old_cmd in s:
    s = s.replace(old_cmd, new_cmd, 1)

# 4) RunInstall：先从输入框取目录
old_run = """static void RunInstall(HWND hwnd) {
    EnableWindow(g_btn, FALSE);
    SetWindowTextW(g_status, L"正在解压…");"""
new_run = """static void RunInstall(HWND hwnd) {
    if (g_pathEdit) {
        wchar_t buf[MAX_PATH * 2] = {};
        GetWindowTextW(g_pathEdit, buf, MAX_PATH * 2);
        std::wstring dir = buf;
        while (!dir.empty() && (dir.back() == L' ' || dir.back() == L'"')) dir.pop_back();
        if (dir.size() < 4 || dir.find(L':') == std::wstring::npos) {
            MessageBoxW(hwnd, L"请先选择一个有效的安装目录。", L"TackShot", MB_ICONWARNING);
            return;
        }
        g_installRoot = dir;
        LogW(L"install dir = %ls", dir.c_str());
    }
    EnableWindow(g_btn, FALSE);
    SetWindowTextW(g_status, L"正在解压…");"""
if old_run in s:
    s = s.replace(old_run, new_run, 1)

io.open(p, "w", encoding="utf-8").write(s)
print("installer dir picker added")
