import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
start = s.index("    int dpIdx = args.indexOf(\"--overlay-dpi-probe\");")
end = s.index("    // 拉框实时性自检")
new = r'''    int dpIdx = args.indexOf("--overlay-dpi-probe");
    if (dpIdx >= 0) {
        QString out = (dpIdx + 1 < args.size()) ? args[dpIdx + 1] : "probe.txt";
        QScreen* sc = QGuiApplication::primaryScreen();
        qreal dpr = sc->devicePixelRatio();
        QRect phys(int(sc->geometry().x() * dpr), int(sc->geometry().y() * dpr),
                   int(sc->geometry().width() * dpr), int(sc->geometry().height() * dpr));
        QImage shot(phys.size(), QImage::Format_RGB32);
        shot.fill(QColor("#3355aa"));
        auto* ov = new Overlay(shot, phys, dpr);
        ov->setTargetScreen(sc);
        ov->show();
        QCoreApplication::processEvents();
        QThread::msleep(200);
        QCoreApplication::processEvents();

        HWND hw = (HWND)ov->winId();
        RECT wr{};
        GetWindowRect(hw, &wr);
        QWindow* h = ov->windowHandle();

        QString info = QString("screen=%1 screenDpr=%2 screenGeom=%3,%4 %5x%6\n"
                               "physRect=%7,%8 %9x%10\n"
                               "widgetGeom=%11,%12 %13x%14 widgetDpr=%15\n"
                               "windowDpr=%16\n"
                               "win32Rect=%17,%18 %19x%20\n")
                           .arg(sc->name()).arg(dpr)
                           .arg(sc->geometry().x()).arg(sc->geometry().y())
                           .arg(sc->geometry().width()).arg(sc->geometry().height())
                           .arg(phys.x()).arg(phys.y()).arg(phys.width()).arg(phys.height())
                           .arg(ov->x()).arg(ov->y()).arg(ov->width()).arg(ov->height())
                           .arg(ov->devicePixelRatioF())
                           .arg(h ? h->devicePixelRatio() : -1.0)
                           .arg(wr.left).arg(wr.top)
                           .arg(wr.right - wr.left).arg(wr.bottom - wr.top);
        QFile f(out);
        if (f.open(QIODevice::WriteOnly)) { f.write(info.toUtf8()); f.close(); }
        ov->hide();
        return 0;
    }

'''
s = s[:start] + new + s[end:]
if "#include <windows.h>" not in s:
    s = s.replace("#include <QtWidgets>", "#include <QtWidgets>\n#include <windows.h>")
io.open(p, "w", encoding="utf-8").write(s)
print("probe rewritten")
