import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()

# 1) 抽出屏物理矩形 helper（放在 makeAppIcon 之前）
helper = """static QRect screenPhysicalRect(QScreen* s) {
    const qreal d = s->devicePixelRatio();
    const QRect g = s->geometry();
    return QRect(QPoint(qRound(g.x() * d), qRound(g.y() * d)),
                 QSize(qRound(g.width() * d), qRound(g.height() * d)));
}

static QIcon makeAppIcon() {"""
s = s.replace("static QIcon makeAppIcon() {", helper, 1)

# 2) doCapture 使用 helper
s = s.replace("""            const qreal sd = cur->devicePixelRatio();
            QRect g = cur->geometry();
            QRect phys(QPoint(qRound(g.x() * sd), qRound(g.y() * sd)),
                       QSize(qRound(g.width() * sd), qRound(g.height() * sd)));""",
"""            const qreal sd = cur->devicePixelRatio();
            QRect phys = screenPhysicalRect(cur);""")

# 3) dpi-selftest 改为逐屏验证
start = s.index("    // DPI 自检：校验物理/逻辑坐标换算")
end = s.index("    // 音频自检：播放 1kHz 音调")
newblock = """    // DPI 自检：逐屏校验 物理=逻辑×dpr，以及覆盖层映射比例
    int dpiIdx = args.indexOf("--dpi-selftest");
    if (dpiIdx >= 0) {
        QString out = (dpiIdx + 1 < args.size()) ? args[dpiIdx + 1] : "dpi.txt";
        QRect virt;
        QImage shot = capture::captureVirtualDesktop(&virt, nullptr);
        const auto screens = QGuiApplication::screens();
        bool allPass = true;

        QFile rf(out);
        rf.open(QIODevice::WriteOnly);
        QTextStream ts(&rf);
        ts.setEncoding(QStringConverter::Utf8);
        ts << "screens=" << screens.size() << " capture=" << shot.width() << "x" << shot.height()
           << " virt=" << virt.x() << "," << virt.y() << "\\n";

        for (QScreen* sc : screens) {
            const qreal dpr = sc->devicePixelRatio();
            QRect phys = screenPhysicalRect(sc);
            QRect inShot = phys.translated(-virt.topLeft());
            bool inside = shot.rect().contains(inShot);
            QImage part = inside && !shot.isNull() ? shot.copy(inShot) : QImage();

            ts << "screen " << sc->name() << "\\n";
            ts << "  logical=" << sc->geometry().x() << "," << sc->geometry().y() << " "
               << sc->geometry().width() << "x" << sc->geometry().height() << " dpr=" << dpr << "\\n";
            ts << "  physical=" << phys.x() << "," << phys.y() << " " << phys.width() << "x" << phys.height()
               << " insideCapture=" << (inside ? "true" : "false") << "\\n";

            if (!inside || part.isNull()) { ts << "  pass=false (超出抓屏范围)\\n"; allPass = false; continue; }

            auto* ov = new Overlay(part, phys, dpr);
            QPoint wpt(100, 60);
            QPoint ipt = ov->demoMapToImage(wpt);
            double ratio = wpt.x() ? double(ipt.x()) / wpt.x() : 0;
            double errW = qAbs(ov->width() * dpr - part.width());
            bool pass = (qAbs(ratio - dpr) < 0.02) && (errW <= 2.0);
            ts << "  overlayLogical=" << ov->width() << "x" << ov->height()
               << " scale=" << ov->demoScale()
               << " mapRatio=" << ratio << " widthError=" << errW
               << " pass=" << (pass ? "true" : "false") << "\\n";
            if (!pass) allPass = false;
            ov->deleteLater();
        }
        ts << "ALL_PASS=" << (allPass ? "true" : "false") << "\\n";
        rf.close();
        return allPass ? 0 : 12;
    }

"""
s = s[:start] + newblock + s[end:]
io.open(p, "w", encoding="utf-8").write(s)
print("dpi selftest rewritten")
