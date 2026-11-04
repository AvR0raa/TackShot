import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\tools\build.ps1"
s = io.open(p, encoding="utf-8").read()
s = s.replace('"settingsdialog.h", "sessions.h"', '"settingsdialog.h", "sessions.h", "translate.h"')
s = s.replace('"-lmfplat","-lmfreadwrite","-lmfuuid","-lpropsys","-lshlwapi","-lwinmm",',
              '"-lmfplat","-lmfreadwrite","-lmfuuid","-lpropsys","-lshlwapi","-lwinmm","-lcrypt32",')
io.open(p, "w", encoding="utf-8").write(s)
print("build fixed")
