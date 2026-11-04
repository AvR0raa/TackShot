import io

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\pinwindow.h"
s = io.open(p, encoding="utf-8").read()
if "demoShowChrome" not in s:
    s = s.replace("    void placeAt(const QPoint& globalPos);",
                  "    void placeAt(const QPoint& globalPos);\n    void demoShowChrome() { m_hover = true; m_reveal = 1.0; m_hoverBtn = -1; update(); }")
io.open(p, "w", encoding="utf-8").write(s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("            pin->grab().toImage().save(outdir + \"/pin.png\");",
              "            pin->demoShowChrome();\n            QCoreApplication::processEvents();\n            pin->grab().toImage().save(outdir + \"/pin.png\");")
io.open(p, "w", encoding="utf-8").write(s)
print("pin chrome demo added")
