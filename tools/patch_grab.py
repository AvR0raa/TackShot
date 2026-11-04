import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\sessions.cpp"
s = io.open(p, encoding="utf-8").read()
old = """QImage grabRegion(const QRect& physRegion) {
    QRect virt;
    QImage full = capture::captureVirtualDesktop(&virt, nullptr);"""
new = """QImage grabRegion(const QRect& physRegion) {
    // 小区域用 GDI 直接抓（录制每 66ms 一次，全屏回读太慢）
    QImage img = capture::captureRect(physRegion);
    if (!img.isNull()) return img;
    QRect virt;
    QImage full = capture::captureVirtualDesktop(&virt, nullptr);"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("patched")
else:
    print("MISS")
