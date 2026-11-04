import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace('#include "ocr.h"', '#include "ocrline.h"')
io.open(p, "w", encoding="utf-8").write(s)
print("overlay.h include fixed")
