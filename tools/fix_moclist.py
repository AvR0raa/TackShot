import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\tools\build.ps1"
s = io.open(p, encoding="utf-8").read()
if '"ocrdialog.h"' not in s:
    s = s.replace('"sessions.h", "translate.h", "theme.h")',
                  '"sessions.h", "translate.h", "theme.h", "ocrdialog.h")')
    io.open(p, "w", encoding="utf-8").write(s)
print("build.ps1 moc list:", "ocrdialog.h" in io.open(p, encoding="utf-8").read())
