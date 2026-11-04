import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.cpp"
s = io.open(p, encoding="utf-8").read()
if '#include "common.h"' not in s:
    s = s.replace('#include "config.h"', '#include "common.h"\n#include "config.h"')
io.open(p, "w", encoding="utf-8").write(s)
print("common.h included")
