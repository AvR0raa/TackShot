import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
anchor = "    // 拉框实时性自检"
code = r'''    // 覆盖层 DPI 探针：真实创建一次覆盖层，记录窗口实际 DPR 与几何
    int dpIdx = args.indexOf("--overlay-dpi-probe");
    if (dpIdx >= 0) {
        QString out = (dpIdx + 1 < args.size()) ? args[dpIdx + 1] : "probe.txt";
        QScreen* sc = QGuiApplication::primaryScreen();
        QRect phys(QPoint(int(sc->geometry().x() * sc->devicePixelRatio()),
                          int(sc->geometry().y() * sc->devicePixelRatio())),
                   QSize(int(sc->geometry().width() * sc->devicePixelRatio()),
                         int(sc->geometry().height() * sc->devicePixelRatio())));
        QImage shot(phys.size(), QImage::Format_RGB32);
        shot.fill(QColor("#3355aa"));
        auto* ov = new Overlay(shot, phys, sc->devicePixelRatio());
        ov->setTargetScreen(sc);
        ov->show();
        QElapsedTimer t; t.start();
        while (t.elapsed() < 400) QCoreApplication::processEvents(QEventLoop::AllEvents, 20);

        QWindow* h = ov->windowHandle();
        QString info = QString("screen=%1 screenDpr=%2 screenGeom=%3,%4 %5x%6\n"
                               "physRect=%7,%8 %9x%10\n"
                               "widgetGeom=%11,%12 %13x%14 widgetDpr=%15\n"
                               "windowDpr=%16 nativeGeom=%17,%18 %19x%20\n")
                           .arg(sc->name()).arg(sc->devicePixelRatio())
                           .arg(sc->geometry().x()).arg(sc->geometry().y())
                           .arg(sc->geometry().width()).arg(sc->geometry().height())
                           .arg(phys.x()).arg(phys.y()).arg(phys.width()).arg(phys.height())
                           .arg(ov->x()).arg(ov->y()).arg(ov->width()).arg(ov->height())
                           .arg(ov->devicePixelRatioF())
                           .arg(h ? h->devicePixelRatio() : -1.0)
                           .arg(h ? h->x() : -1).arg(h ? h->y() : -1)
                           .arg(h ? h->width() : -1).arg(h ? h->height() : -1);
        QFile f(out);
        if (f.open(QIODevice::WriteOnly)) { f.write(info.toUtf8()); f.close(); }
        ov->close();
        ov->deleteLater();
        return 0;
    }

'''
if anchor in s:
    s = s.replace(anchor, code + anchor, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("dpi probe added")
else:
    print("MISS")
