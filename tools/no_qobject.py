import io
for path in [r"C:\Users\laiki\.dsh\workspace\tackshot\src\baidu.h",
             r"C:\Users\laiki\.dsh\workspace\tackshot\src\simpletex.h"]:
    s = io.open(path, encoding="utf-8").read()
    s = s.replace("    Q_OBJECT\n", "")
    io.open(path, "w", encoding="utf-8").write(s)
print("Q_OBJECT removed (no signals needed)")
