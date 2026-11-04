import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\capture.cpp"
s = io.open(p, encoding="utf-8").read()
decl = 'static QString g_lastPath = QStringLiteral("none");\n'
s = s.replace(decl, "", 1)   # 移除原位置
idx = s.find("namespace capture {")
if idx >= 0 and decl not in s:
    s = s[:idx] + "namespace capture {\n\n" + decl + s[idx + len("namespace capture {"):]
io.open(p, "w", encoding="utf-8").write(s)
print("moved decl, namespace found:", idx >= 0)
