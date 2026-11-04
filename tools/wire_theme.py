import io

# build.ps1: moc 列表加 theme.h
p = r"C:\Users\laiki\.dsh\workspace\tackshot\tools\build.ps1"
s = io.open(p, encoding="utf-8").read()
s = s.replace('@("config.h", "hotkey.h", "overlay.h", "pinwindow.h", "settingsdialog.h", "sessions.h", "translate.h")',
              '@("config.h", "hotkey.h", "overlay.h", "pinwindow.h", "settingsdialog.h", "sessions.h", "translate.h", "theme.h")')
io.open(p, "w", encoding="utf-8").write(s)

# config.h
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\config.h"
s = io.open(p, encoding="utf-8").read()
if "appearance" not in s:
    s = s.replace("    bool showCursorMagnifier = true;",
                  "    bool showCursorMagnifier = true;\n    QString appearance = \"system\";   // system / light / dark")
io.open(p, "w", encoding="utf-8").write(s)

# config.cpp
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\config.cpp"
s = io.open(p, encoding="utf-8").read()
if "appearance" not in s:
    s = s.replace('    o["showCursorMagnifier"] = showCursorMagnifier;',
                  '    o["showCursorMagnifier"] = showCursorMagnifier;\n    o["appearance"] = appearance;')
    s = s.replace('    if (o.contains("showCursorMagnifier")) showCursorMagnifier = o["showCursorMagnifier"].toBool();',
                  '    if (o.contains("showCursorMagnifier")) showCursorMagnifier = o["showCursorMagnifier"].toBool();\n    if (o.contains("appearance")) appearance = o["appearance"].toString();')
io.open(p, "w", encoding="utf-8").write(s)

# main.cpp: 初始化主题
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
if '#include "theme.h"' not in s:
    s = s.replace('#include "config.h"', '#include "config.h"\n#include "theme.h"')
    s = s.replace("    QApplication app(argc, argv);",
                  "    QApplication app(argc, argv);\n    Theme::initFromConfig();\n    Theme::applyGlobal();")
io.open(p, "w", encoding="utf-8").write(s)
print("theme wired into build/config/main")
