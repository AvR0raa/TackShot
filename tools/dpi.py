import io

# 1) Overlay：暴露映射自检 + 用传入 dpr 计算几何（已有）
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    QVector<int> demoUndoTest();",
              "    QVector<int> demoUndoTest();\n"
              "    // 自检：把窗口坐标映射成图像坐标（与鼠标逻辑同一条路径）\n"
              "    QPoint demoMapToImage(const QPoint& widgetPos) const { return toImage(widgetPos); }\n"
              "    QRect  demoPhysicalRect() const { return m_physRect; }\n"
              "    qreal  demoScale() const { return m_scale; }")
io.open(p, "w", encoding="utf-8").write(s)

# 2) main.cpp：混合 DPI 下只抓光标所在屏 + dpi 自检
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()

old = """    qreal dpr = 1.0;
    if (QScreen* s = QGuiApplication::primaryScreen()) dpr = s->devicePixelRatio();
    showOverlay(shot, rect, dpr);"""
new = """    qreal dpr = 1.0;
    if (QScreen* s = QGuiApplication::primaryScreen()) dpr = s->devicePixelRatio();

    // 混合 DPI：各屏缩放不同时，覆盖层只覆盖光标所在屏，避免整体缩放导致错位
    const auto screens = QGuiApplication::screens();
    bool mixed = false;
    for (QScreen* s : screens)
        if (!qFuzzyCompare(s->devicePixelRatio(), dpr)) { mixed = true; break; }
    if (mixed) {
        QScreen* cur = QGuiApplication::screenAt(QCursor::pos());
        if (!cur) cur = QGuiApplication::primaryScreen();
        if (cur) {
            const qreal sd = cur->devicePixelRatio();
            QRect g = cur->geometry();
            QRect phys(QPoint(qRound(g.x() * sd), qRound(g.y() * sd)),
                       QSize(qRound(g.width() * sd), qRound(g.height() * sd)));
            QRect inShot = phys.translated(-rect.topLeft());
            if (shot.rect().contains(inShot) && inShot.width() > 16 && inShot.height() > 16) {
                shot = shot.copy(inShot);
                rect = phys;
                dpr = sd;
            }
        }
    }
    showOverlay(shot, rect, dpr);"""
if old in s:
    s = s.replace(old, new, 1)

anchor = "    // 音频自检：播放 1kHz 音调"
code = """    // DPI 自检：校验物理/逻辑坐标换算（可用 QT_SCALE_FACTOR 模拟其它缩放比）
    int dpiIdx = args.indexOf("--dpi-selftest");
    if (dpiIdx >= 0) {
        QString out = (dpiIdx + 1 < args.size()) ? args[dpiIdx + 1] : "dpi.txt";
        QRect virt;
        QImage shot = capture::captureVirtualDesktop(&virt, nullptr);
        QScreen* primary = QGuiApplication::primaryScreen();
        qreal dpr = primary ? primary->devicePixelRatio() : 1.0;
        QRect screenGeom = primary ? primary->geometry() : QRect(0, 0, shot.width(), shot.height());

        QImage synth = shot.isNull() ? QImage(2560, 1440, QImage::Format_RGB32) : shot;
        auto* ov = new Overlay(synth, QRect(0, 0, synth.width(), synth.height()), dpr);

        // 取一个窗口坐标，映射到图像坐标，检查比例是否等于 dpr
        QPoint widgetPt(100, 60);
        QPoint imgPt = ov->demoMapToImage(widgetPt);
        double ratioX = widgetPt.x() ? double(imgPt.x()) / widgetPt.x() : 0;

        // 覆盖层逻辑尺寸 * dpr 是否≈图像尺寸
        double expectW = ov->width() * dpr;
        double errW = qAbs(expectW - synth.width());

        QFile rf(out);
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts.setEncoding(QStringConverter::Utf8);
            ts << "screens=" << QGuiApplication::screens().size() << "\\n";
            for (QScreen* s : QGuiApplication::screens())
                ts << "  screen " << s->name() << " geom=" << s->geometry().x() << "," << s->geometry().y()
                   << " " << s->geometry().width() << "x" << s->geometry().height()
                   << " dpr=" << s->devicePixelRatio() << "\\n";
            ts << "capture=" << shot.width() << "x" << shot.height() << " virt="
               << virt.x() << "," << virt.y() << "\\n";
            ts << "overlayLogical=" << ov->width() << "x" << ov->height()
               << " scale=" << ov->demoScale() << " dpr=" << dpr << "\\n";
            ts << "map widget(100,60) -> image(" << imgPt.x() << "," << imgPt.y()
               << ") ratio=" << ratioX << "\\n";
            ts << "widthError=" << errW << "\\n";
            bool pass = (qAbs(ratioX - dpr) < 0.02) && (errW <= 2.0);
            ts << "pass=" << (pass ? "true" : "false") << "\\n";
            rf.close();
        }
        ov->deleteLater();
        return 0;
    }

    // 音频自检：播放 1kHz 音调"""
if anchor in s:
    s = s.replace(anchor, code + anchor, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("dpi handling + selftest added")
