import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
if "#include <QWindow>" not in s:
    s = s.replace('#include "common.h"', '#include "common.h"\n#include <QWindow>', 1)
io.open(p, "w", encoding="utf-8").write(s)
print("QWindow added:", "#include <QWindow>" in s)
