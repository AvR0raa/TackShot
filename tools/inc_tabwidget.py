import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
if "#include <QTabWidget>" not in s:
    s = s.replace('#include "overlay.h"', '#include "overlay.h"\n#include <QTabWidget>', 1)
    io.open(p, "w", encoding="utf-8").write(s)
print("QTabWidget include:", "#include <QTabWidget>" in io.open(p, encoding="utf-8").read())
