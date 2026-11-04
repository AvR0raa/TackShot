import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
anchor = "    // 录制方向自检"
code = r'''    // 标注自检：模拟鼠标手势，逐工具渲染，验证箭头/画笔/马赛克
    int anIdx = args.indexOf("--annot-selftest");
    if (anIdx >= 0) {
        QString outdir = (anIdx + 1 < args.size()) ? args[anIdx + 1] : ".";
        QDir().mkpath(outdir);
        QImage base(1400, 900, QImage::Format_RGB32);
        base.fill(Qt::white);
        {
            QPainter p(&base);
            p.setPen(QColor(230, 230, 230));
            for (int x = 0; x < base.width(); x += 50) p.drawLine(x, 0, x, base.height());
            for (int y = 0; y < base.height(); y += 50) p.drawLine(0, y, base.width(), y);
        }

        auto* ov = new Overlay(base, QRect(0, 0, 1400, 900), 1.0);
        ov->demoSelect(QRect(100, 60, 1200, 760));

        struct Case { Tool t; const char* name; QVector<QPoint> pts; };
        QVector<Case> cases;
        cases.append({Tool::Arrow, "arrow", {QPoint(320, 300), QPoint(700, 300), QPoint(700, 300), QPoint(700, 430)}});
        cases.append({Tool::Line, "line", {QPoint(900, 200), QPoint(1100, 380)}});
        {
            QVector<QPoint> pen;
            for (int i = 0; i < 30; ++i) pen.append(QPoint(300 + i * 18, 600 + int(qSin(i * 0.4) * 45)));
            cases.append({Tool::Pen, "pen", pen});
        }
        {
            QVector<QPoint> mos;
            for (int i = 0; i < 18; ++i) mos.append(QPoint(900 + i * 14, 560 + i * 6));
            cases.append({Tool::Mosaic, "mosaic", mos});
        }

        QStringList log;
        for (const Case& c : cases) {
            ov->demoSetTool(c.t);
            ov->demoSimPress(c.pts.first());
            for (int i = 1; i < c.pts.size(); ++i) ov->demoSimMove(c.pts[i]);
            ov->demoSimRelease(c.pts.last());

            QImage img = ov->demoFinal();
            img.save(QString("%1/annot_%2.png").arg(outdir, QString::fromLatin1(c.name)));
            QString detail;
            if (ov->demoAnnotCount() > 0) {
                Annotation a = ov->demoAnnot(ov->demoAnnotCount() - 1);
                detail = QString("type=%1 pts=%2").arg(int(a.type)).arg(a.pts.size());
            }
            log << QString("%1: annots=%2 %3").arg(QString::fromLatin1(c.name))
                       .arg(ov->demoAnnotCount()).arg(detail);
        }
        ov->deleteLater();

        QFile rf(outdir + "/annot_report.txt");
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts.setEncoding(QStringConverter::Utf8);
            for (const QString& l : log) ts << l << "\n";
            rf.close();
        }
        return 0;
    }

'''
if anchor in s:
    s = s.replace(anchor, code + anchor, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("annot selftest added")
else:
    print("MISS")
