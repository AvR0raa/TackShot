import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\setup\setup_w32.cpp"
s = io.open(p, encoding="utf-8").read()
old = """        if (dir.size() < 4 || dir.find(L':') == std::wstring::npos) {"""
new = """        bool looksAbsolute = (dir.find(L':') != std::wstring::npos) ||
                             (dir.size() > 2 && dir[0] == L'\\\\' && dir[1] == L'\\\\');
        if (dir.size() < 4 || !looksAbsolute) {"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("validation relaxed")
else:
    print("MISS")
