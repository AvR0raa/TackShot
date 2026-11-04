import io

# capture.h/cpp：暴露抓屏路径与 DPI 感知状态
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\capture.h"
s = io.open(p, encoding="utf-8").read()
if "lastPath" not in s:
    s = s.replace("QRect nativeWindowRect(quintptr hwnd);",
"""QRect nativeWindowRect(quintptr hwnd);

// 上一次抓屏走的路径："dxgi" / "gdi"
QString lastPath();

// 进程/线程 DPI 感知状态描述
QString dpiAwarenessInfo();""")
io.open(p, "w", encoding="utf-8").write(s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\capture.cpp"
s = io.open(p, encoding="utf-8").read()
if "lastPath" not in s:
    s = s.replace("QRect nativeWindowRect(quintptr id) {",
"""static QString g_lastPath = QStringLiteral("none");
QString lastPath() { return g_lastPath; }

QString dpiAwarenessInfo() {
    QStringList parts;
    DPI_AWARENESS_CONTEXT ctx = GetThreadDpiAwarenessContext();
    DPI_AWARENESS aw = GetAwarenessFromDpiAwarenessContext(ctx);
    switch (aw) {
    case DPI_AWARENESS_UNAWARE: parts << "thread=unaware"; break;
    case DPI_AWARENESS_SYSTEM_AWARE: parts << "thread=system"; break;
    case DPI_AWARENESS_PER_MONITOR_AWARE: parts << "thread=permonitor"; break;
    default: parts << "thread=?"; break;
    }
    parts << QString("threadDpi=%1").arg(GetDpiForSystem());
    HDC dc = GetDC(nullptr);
    if (dc) {
        parts << QString("dcCaps=%1x%2").arg(GetDeviceCaps(dc, HORZRES)).arg(GetDeviceCaps(dc, VERTRES));
        parts << QString("desktopDpi=%1").arg(GetDeviceCaps(dc, LOGPIXELSX));
        ReleaseDC(nullptr, dc);
    }
    return parts.join(" ");
}

QRect nativeWindowRect(quintptr id) {""")
io.open(p, "w", encoding="utf-8").write(s)
print("capture helpers added")
