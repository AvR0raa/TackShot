import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
if "#include <QWindow>" not in s:
    s = s.replace("#include <QtWidgets>", "#include <QtWidgets>\n#include <QWindow>")
io.open(p, "w", encoding="utf-8").write(s)
print("QWindow included")
