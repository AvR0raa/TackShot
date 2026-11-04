import io

# capture.h：加一个物理窗口矩形查询
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\capture.h"
s = io.open(p, encoding="utf-8").read()
if "nativeWindowRect" not in s:
    s = s.replace("}  // namespace capture", "// 原生窗口在屏幕坐标系里的物理矩形（用于 DPI 校验）\nQRect nativeWindowRect(quintptr hwnd);\n\n}  // namespace capture")
io.open(p, "w", encoding="utf-8").write(s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\capture.cpp"
s = io.open(p, encoding="utf-8").read()
if "nativeWindowRect" not in s:
    s = s.replace("}  // namespace capture",
"""QRect nativeWindowRect(quintptr id) {
    RECT r{};
    if (GetWindowRect(reinterpret_cast<HWND>(id), &r))
        return QRect(r.left, r.top, r.right - r.left, r.bottom - r.top);
    return QRect();
}

}  // namespace capture""")
io.open(p, "w", encoding="utf-8").write(s)

# main.cpp：去掉 windows.h，改用 capture::nativeWindowRect
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("#include <QtWidgets>\n#include <windows.h>", "#include <QtWidgets>")
s = s.replace("""        HWND hw = (HWND)ov->winId();
        RECT wr{};
        GetWindowRect(hw, &wr);
        QWindow* h = ov->windowHandle();""",
"""        QRect wr = capture::nativeWindowRect(quintptr(ov->winId()));
        QWindow* h = ov->windowHandle();""")
s = s.replace("""                           .arg(wr.left).arg(wr.top)
                           .arg(wr.right - wr.left).arg(wr.bottom - wr.top);""",
"""                           .arg(wr.x()).arg(wr.y()).arg(wr.width()).arg(wr.height());""")
io.open(p, "w", encoding="utf-8").write(s)
print("probe now uses capture helper")
