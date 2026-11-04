import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.h"
s = io.open(p, encoding="utf-8").read()
if "class QLabel;" not in s:
    s = s.replace("class QSpinBox;", "class QSpinBox;\nclass QLabel;")
io.open(p, "w", encoding="utf-8").write(s)
print("qlabel declared")
