import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
old = """        QRect mon = capture::nativeMonitorRect(quintptr(winId()));
        if (mon.isValid() && mon.width() > 100) {"""
new = """        QRect mon = capture::nativeMonitorRect(quintptr(winId()));
        // 只有“覆盖整块显示器”的情况才用显示器矩形校正：
        // 若抓到的区域比显示器小（例如输出带黑边、已裁掉），必须保持原尺寸，否则内容会被拉伸。
        const bool coversMonitor = mon.isValid() && mon.width() > 100 &&
                                   qAbs(mon.width() - m_physRect.width()) < 64 &&
                                   qAbs(mon.height() - m_physRect.height()) < 64;
        if (coversMonitor) {"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("monitor correction guarded")
else:
    print("MISS")
