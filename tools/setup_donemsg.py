import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\setup\setup_w32.cpp"
s = io.open(p, encoding="utf-8").read()

old = """    if (MessageBoxW(hwnd, L"TackShot 安装完成，是否立即启动？\\n\\n默认热键：Ctrl+Alt+A（可在设置中修改）",
                    L"TackShot", MB_YESNO | MB_ICONINFORMATION) == IDYES) {"""
new = """    {
        std::wstring doneMsg = L"TackShot 安装完成。\\n\\n安装目录：\\n" + root +
                               L"\\n\\n默认热键：Ctrl+Alt+A（可在设置中修改）\\n\\n是否立即启动？";
        if (MessageBoxW(hwnd, doneMsg.c_str(), L"TackShot", MB_YESNO | MB_ICONINFORMATION) == IDYES) {
            ShellExecuteW(nullptr, L"open", (root + L"\\\\TackShot.exe").c_str(), nullptr, root.c_str(), SW_SHOWNORMAL);
            DestroyWindow(hwnd);
            return;
        }
    }
    if (false) {"""
if old in s:
    s = s.replace(old, new, 1)
    # 删掉原来那段 body 结尾
    s = s.replace("""    if (false) {
        ShellExecuteW(nullptr, L"open", (root + L"\\\\TackShot.exe").c_str(), nullptr, root.c_str(), SW_SHOWNORMAL);
    }
    DestroyWindow(hwnd);""", """    DestroyWindow(hwnd);""")
    io.open(p, "w", encoding="utf-8").write(s)
    print("done message now shows path")
else:
    print("MISS")
