import io

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.h"
s = io.open(p, encoding="utf-8").read()
if "demoSel()" not in s:
    s = s.replace("    int demoSelected() const { return m_selected; }",
                  "    int demoSelected() const { return m_selected; }\n    QRect demoSel() const { return m_sel; }")
io.open(p, "w", encoding="utf-8").write(s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
anchor = "    // 纯抓屏诊断"
code = r'''    // 拖拽抖动自检：按 1px 步进拖 40 次，检查选区是否单调、无回跳
    int dgIdx = args.indexOf("--drag-selftest");
    if (dgIdx >= 0) {
        QString out = (dgIdx + 1 < args.size()) ? args[dgIdx + 1] : "drag.txt";
        QImage base(2000, 1400, QImage::Format_RGB32);
        base.fill(QColor("#203040"));
        auto* ov = new Overlay(base, QRect(0, 0, 2000, 1400), 1.25);
        ov->demoSelect(QRect(400, 300, 600, 400));

        ov->demoSimPress(QPoint(700, 500));
        QStringList seq;
        int prev = ov->demoSel().left();
        int backSteps = 0, sameSteps = 0, widthChanges = 0;
        const int startW = ov->demoSel().width();
        for (int i = 1; i <= 40; ++i) {
            ov->demoSimMove(QPoint(700 + i, 500));
            int x = ov->demoSel().left();
            seq << QString::number(x);
            if (x < prev) backSteps++;
            if (x == prev) sameSteps++;
            if (ov->demoSel().width() != startW) widthChanges++;
            prev = x;
        }
        ov->demoSimRelease(QPoint(740, 500));
        ov->deleteLater();

        QFile f(out);
        if (f.open(QIODevice::WriteOnly)) {
            QTextStream ts(&f);
            ts << "x sequence: " << seq.join(",") << "\n";
            ts << "backSteps=" << backSteps << " sameSteps=" << sameSteps
               << " widthChanges=" << widthChanges << "\n";
            ts << "PASS=" << ((backSteps == 0 && widthChanges == 0) ? "true" : "false") << "\n";
            f.close();
        }
        return 0;
    }

'''
if anchor in s:
    s = s.replace(anchor, code + anchor, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("drag selftest added")
else:
    print("MISS")
