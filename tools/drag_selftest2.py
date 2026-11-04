import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
start = s.index("    int dgIdx = args.indexOf(\"--drag-selftest\");")
end = s.index("    // 纯抓屏诊断")
new = r'''    int dgIdx = args.indexOf("--drag-selftest");
    if (dgIdx >= 0) {
        QString out = (dgIdx + 1 < args.size()) ? args[dgIdx + 1] : "drag.txt";
        QStringList log;
        bool allPass = true;

        for (qreal dpr : {1.0, 1.25, 1.5}) {
            QImage base(2000, 1400, QImage::Format_RGB32);
            base.fill(QColor("#203040"));
            auto* ov = new Overlay(base, QRect(0, 0, 2000, 1400), dpr);

            const QRect startSel(400, 300, 600, 400);
            ov->demoSelect(startSel);
            const QPoint press(700, 500);           // 位于选区内（逻辑坐标）
            ov->demoSimPress(press);

            // 沿 x 拖 40 个逻辑像素
            const int steps = 40;
            int backSteps = 0, widthChanges = 0, prev = ov->demoSel().left();
            for (int i = 1; i <= steps; ++i) {
                ov->demoSimMove(QPoint(press.x() + i, press.y()));
                int x = ov->demoSel().left();
                if (x < prev) backSteps++;
                if (ov->demoSel().size() != startSel.size()) widthChanges++;
                prev = x;
            }

            QRect moved = ov->demoSel();
            // 期望：向左移动 steps 个逻辑像素（换算到图像坐标）
            const int expectedDx = qRound(steps * dpr);
            const int expectedLeft = startSel.left() + expectedDx;
            // 允许 ±2 的取整误差
            bool follows = qAbs(moved.left() - expectedLeft) <= 2;
            bool sizeKept = moved.size() == startSel.size();
            bool noBack = (backSteps == 0);
            bool pass = follows && sizeKept && noBack;
            allPass &= pass;

            log << QString("dpr=%1 start=%2,%3 movedTo=%4,%5 expectedX=%6 dy=%7 sizeOk=%8 back=%9 pass=%10")
                       .arg(dpr).arg(startSel.x()).arg(startSel.y())
                       .arg(moved.x()).arg(moved.y()).arg(expectedLeft).arg(moved.y() - startSel.y())
                       .arg(sizeKept ? "yes" : "no").arg(backSteps).arg(pass ? "true" : "false");

            // 竖直方向也走一段
            ov->demoSimRelease(QPoint(press.x() + steps, press.y()));
            ov->deleteLater();
        }

        log << QString("ALL_PASS=%1").arg(allPass ? "true" : "false");
        QFile f(out);
        if (f.open(QIODevice::WriteOnly)) {
            QTextStream ts(&f);
            for (const QString& l : log) ts << l << "\n";
            f.close();
        }
        return allPass ? 0 : 19;
    }

'''
s = s[:start] + new + s[end:]
io.open(p, "w", encoding="utf-8").write(s)
print("drag selftest rewritten with assertions")
