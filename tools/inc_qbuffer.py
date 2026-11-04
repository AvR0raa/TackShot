import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\baidu.cpp"
s = io.open(p, encoding="utf-8").read()
if "#include <QBuffer>" not in s:
    s = s.replace("#include <QCryptographicHash>", "#include <QBuffer>\n#include <QCryptographicHash>")
    io.open(p, "w", encoding="utf-8").write(s)
print("QBuffer included")
