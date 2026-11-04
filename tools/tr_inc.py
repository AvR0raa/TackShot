import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
if "#include <QLabel>" not in s:
    s = s.replace("#include <QPlainTextEdit>", "#include <QPlainTextEdit>\n#include <QLabel>\n#include <QApplication>")
io.open(p, "w", encoding="utf-8").write(s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.cpp"
s = io.open(p, encoding="utf-8").read()
if "#include <QApplication>" not in s:
    s = s.replace("#include <QLabel>", "#include <QLabel>\n#include <QApplication>")
io.open(p, "w", encoding="utf-8").write(s)
print("includes added")
