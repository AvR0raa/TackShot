import io

# ---------- config ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\config.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    bool importPixPinDefaults = true;\n", "")
io.open(p, "w", encoding="utf-8").write(s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\config.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace('    o["importPixPinDefaults"] = importPixPinDefaults;\n', "")
s = s.replace('    if (o.contains("importPixPinDefaults")) importPixPinDefaults = o["importPixPinDefaults"].toBool();\n', "")
s = s.replace("""    } else {
        // 首次运行：尝试读取 PixPin 的配置作为样式默认值（兼容）
        importPixPinIfPossible();
        save();
    }""",
"""    } else {
        save();
    }""")
start = s.find("// 兼容：读取 PixPin 的 PixPinConfig.json")
if start >= 0:
    s = s[:start].rstrip() + "\n"
io.open(p, "w", encoding="utf-8").write(s)

# ---------- main.cpp ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace('#include "hisimport.h"\n', "")
start = s.find("// ---------------- PixPin")
if start >= 0:
    end = s.find("int main(int argc, char** argv) {")
    s = s[:start] + s[end:]
s = s.replace("""    menu->addAction(QStringLiteral("导入 PixPin 历史…"), []() {
        HistoryDialog dlg;
        dlg.exec();
    });
""", "")
io.open(p, "w", encoding="utf-8").write(s)
print("code cleaned")

# ---------- README：按行过滤 ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\README.md"
lines = io.open(p, encoding="utf-8").read().split("\n")
out = []
for ln in lines:
    if "PixPin 配置兼容" in ln: continue
    if "PixPin 历史兼容" in ln: continue
    if "hisimport.cpp" in ln: continue
    out.append(ln)
io.open(p, "w", encoding="utf-8").write("\n".join(out))
print("readme cleaned")
