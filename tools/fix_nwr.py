import io

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\capture.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("} // namespace capture",
"""// 原生窗口在屏幕坐标下的物理矩形（DPI 校验用）
QRect nativeWindowRect(quintptr hwnd);

} // namespace capture""")
io.open(p, "w", encoding="utf-8").write(s)
print("declared:", "nativeWindowRect" in s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\capture.cpp"
s = io.open(p, encoding="utf-8").read()
if "nativeWindowRect" not in s:
    s = s.replace("} // namespace capture",
"""QRect nativeWindowRect(quintptr id) {
    RECT r{};
    if (GetWindowRect(reinterpret_cast<HWND>(id), &r))
        return QRect(r.left, r.top, int(r.right - r.left), int(r.bottom - r.top));
    return QRect();
}

} // namespace capture""")
io.open(p, "w", encoding="utf-8").write(s)
print("defined:", "nativeWindowRect" in s)
