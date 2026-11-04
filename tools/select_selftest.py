import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
anchor = "    // 标注自检：模拟鼠标手势"
code = r'''    // 拉框实时性自检：按下+移动（不松开）时就应该能看到选区
    int ssIdx = args.indexOf("--select-selftest");
    if (ssIdx >= 0) {
        QString outdir = (ssIdx + 1 < args.size()) ? args[ssIdx + 1] : ".";
        QDir().mkpath(outdir);
        QImage base(1000, 700, QImage::Format_RGB32);
        base.fill(QColor("#2b3a55"));
        {
            QPainter p(&base);
            p.setPen(QColor(255, 255, 255, 60));
            for (int x = 0; x < base.width(); x += 40) p.drawLine(x, 0, x, base.height());
            for (int y = 0; y < base.height(); y += 40) p.drawLine(0, y, base.width(), y);
        }
        auto* ov = new Overlay(base, QRect(0, 0, 1000, 700), 1.0);
        ov->show();
        ov->demoSimPress(QPoint(200, 150));
        ov->demoSimMove(QPoint(420, 320));
        ov->demoSimMove(QPoint(650, 480));
        QImage during = ov->grab().toImage();
        during.save(outdir + "/select_during_drag.png");
        ov->demoSimRelease(QPoint(650, 480));
        QImage after = ov->grab().toImage();
        after.save(outdir + "/select_after_release.png");
        ov->deleteLater();

        QFile rf(outdir + "/select_report.txt");
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts << "during=" << during.width() << "x" << during.height() << "\n";
            ts << "after=" << after.width() << "x" << after.height() << "\n";
            rf.close();
        }
        return 0;
    }

'''
if anchor in s:
    s = s.replace(anchor, code + anchor, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("select selftest added")
else:
    print("MISS")
