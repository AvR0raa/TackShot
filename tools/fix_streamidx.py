import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\mfrec.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    unsigned m_streamIndex = 0;", "    unsigned long m_streamIndex = 0;")
io.open(p, "w", encoding="utf-8").write(s)
print("ok")
