import io

# capture.h / cpp：原生显示器物理矩形
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\capture.h"
s = io.open(p, encoding="utf-8").read()
if "nativeMonitorRect" not in s:
    s = s.replace("QRect nativeWindowRect(quintptr hwnd);",
                  "QRect nativeWindowRect(quintptr hwnd);\n\n// 窗口所在显示器在物理像素下的矩形\nQRect nativeMonitorRect(quintptr hwnd);")
io.open(p, "w", encoding="utf-8").write(s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\capture.cpp"
s = io.open(p, encoding="utf-8").read()
if "nativeMonitorRect" not in s:
    s = s.replace("QRect nativeWindowRect(quintptr id) {",
"""QRect nativeMonitorRect(quintptr id) {
    HMONITOR mon = MonitorFromWindow(reinterpret_cast<HWND>(id), MONITOR_DEFAULTTONEAREST);
    MONITORINFO mi{};
    mi.cbSize = sizeof(mi);
    if (mon && GetMonitorInfoW(mon, &mi)) {
        const RECT& r = mi.rcMonitor;
        return QRect(r.left, r.top, int(r.right - r.left), int(r.bottom - r.top));
    }
    return QRect();
}

QRect nativeWindowRect(quintptr id) {""")
io.open(p, "w", encoding="utf-8").write(s)

# overlay.cpp：showEvent 里按显示器物理矩形校正
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
old = """    // 2) 用窗口实际的 DPR 校正几何与坐标换算。
    //    某些情况下 Qt 会给覆盖层 1.0 的 DPR，导致 2048x1152 的窗口只铺满 2560x1440 屏幕的 80%。
    qreal actual = m_scale;
    if (QWindow* h = windowHandle()) actual = h->devicePixelRatio();
    if (actual > 0.1 && qAbs(actual - m_scale) > 0.01) {
        m_scale = actual;
        QRect g(QPoint(qRound(m_physRect.x() / actual), qRound(m_physRect.y() / actual)),
                QSize(qRound(m_physRect.width() / actual), qRound(m_physRect.height() / actual)));
        setGeometry(g);
        updateToolButtons();
        if (m_bar && m_bar->isVisible()) placeToolbar();
        update();
    }"""
new = """    // 2) 用显示器物理矩形反推窗口应有的逻辑尺寸：
    //    即使 Qt 的 DPR 判断有偏差，也要保证窗口铺满整块屏。
    {
        qreal wd = (windowHandle() ? windowHandle()->devicePixelRatio() : m_scale);
        if (wd < 0.1) wd = m_scale > 0.1 ? m_scale : 1.0;
        QRect mon = capture::nativeMonitorRect(quintptr(winId()));
        if (mon.isValid() && mon.width() > 100) {
            QRect want(QPoint(qRound(mon.x() / wd), qRound(mon.y() / wd)),
                       QSize(qRound(mon.width() / wd), qRound(mon.height() / wd)));
            if (geometry() != want) {
                setGeometry(want);
                updateToolButtons();
                if (m_bar && m_bar->isVisible()) placeToolbar();
                update();
            }
            if (width() > 0) m_scale = double(m_shot.width()) / width();
        }
    }"""
if old in s:
    s = s.replace(old, new, 1)
    s = s.replace('#include "config.h"', '#include "config.h"\n#include "capture.h"')
    io.open(p, "w", encoding="utf-8").write(s)
    print("monitor-based geometry correction added")
else:
    print("MISS")
