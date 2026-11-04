import io, os, re

SRC = r"C:\Users\laiki\.dsh\workspace\tackshot\src"

# 1) 新建 ocrline.h
io.open(os.path.join(SRC, "ocrline.h"), "w", encoding="utf-8").write(
"""#pragma once
#include <QString>
#include <QRect>

// 一行识别结果（文字 / 置信度 / 在原图中的像素框）
struct OcrLine {
    QString text;
    float   score = 0.0f;
    QRect   box;
};
""")

# 2) ocrdialog.h 改 include
p = os.path.join(SRC, "ocrdialog.h")
s = io.open(p, encoding="utf-8").read()
s = s.replace('#include "ocr.h"', '#include "ocrline.h"')
io.open(p, "w", encoding="utf-8").write(s)

# 3) 删除本地 OCR / 公式实现
for name in ["ocr.h", "ocr.cpp", "formula.h", "formula.cpp"]:
    fp = os.path.join(SRC, name)
    if os.path.exists(fp):
        os.remove(fp)

# 4) overlay.cpp：去掉 include
p = os.path.join(SRC, "overlay.cpp")
s = io.open(p, encoding="utf-8").read()
s = s.replace('#include "ocr.h"\n', '#include "ocrline.h"\n')
s = s.replace('#include "formula.h"\n', '')
io.open(p, "w", encoding="utf-8").write(s)

# 5) main.cpp：去掉 include 与两个本地自检块
p = os.path.join(SRC, "main.cpp")
s = io.open(p, encoding="utf-8").read()
s = s.replace('#include "ocr.h"\n', '#include "ocrline.h"\n')
s = s.replace('#include "formula.h"\n', '')

def cut_block(src, start_marker):
    i = src.find(start_marker)
    if i < 0:
        return src, False
    # 从该行行首开始
    line_start = src.rfind("\n", 0, i) + 1
    # 找到块结束：下一个顶层 "    // " 注释且后面紧跟 int/const 定义，或 "    int " 变量声明
    j = line_start
    depth = 0
    started = False
    k = line_start
    while k < len(src):
        ch = src[k]
        if ch == '{':
            depth += 1
            started = True
        elif ch == '}':
            depth -= 1
            if started and depth == 0:
                # 到这里块结束（可能还有 return 语句）
                end = src.find("\n", k)
                return src[:line_start] + src[end+1:], True
        k += 1
    return src, False

for marker in ["int ocrIdx = args.indexOf(\"--ocr-selftest\");",
               "int fmIdx = args.indexOf(\"--formula-selftest\");"]:
    s, ok = cut_block(s, marker)
    print("removed", marker[:30], ok)

io.open(p, "w", encoding="utf-8").write(s)
print("local ocr/formula removed")
