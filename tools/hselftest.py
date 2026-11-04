import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
anchor = 'canvas.save(outdir + "/longshot_result.png");'
add = anchor + """

        // ---- 横向：合成一张宽图，按列切帧，用 appendAuto 拼接 ----
        const int HW = 1800, HH = 600, FW = 600, HSTEP = 500;
        QImage wide(HW, HH, QImage::Format_RGB32);
        {
            QPainter p(&wide);
            for (int x = 0; x < HW; ++x) {
                QColor c = QColor::fromHsv((x * 5) % 360, 60, 235 - (x % 40));
                p.fillRect(x, 0, 1, HH, c);
            }
            QFont f(QStringLiteral("Microsoft YaHei"));
            f.setPixelSize(26);
            p.setFont(f);
            p.setPen(Qt::black);
            for (int i = 0; i < 18; ++i)
                p.drawText(60 + i * 96, 120, QString("列 %1").arg(i + 1));
        }
        wide.save(outdir + "/longshot_wide_source.png");

        QImage hcanvas;
        int hmatched = 0, hframes = 0, hdir = -1;
        for (int x = 0; x + FW <= HW; x += HSTEP) {
            QImage frame = wide.copy(x, 0, FW, HH);
            bool m = false;
            int d = 0;
            hcanvas = longshot::appendAuto(hcanvas, frame, &d, &m);
            hframes++;
            if (m) { hmatched++; hdir = d; }
        }
        hcanvas.save(outdir + "/longshot_wide_result.png");

        int hcmpW = qMin(hcanvas.width(), wide.width()), hcmpH = HH;
        long long hdiff = 0, hn = 0;
        for (int y = 0; y < hcmpH; y += 3) {
            const QRgb* a = reinterpret_cast<const QRgb*>(hcanvas.constScanLine(y));
            const QRgb* b = reinterpret_cast<const QRgb*>(wide.constScanLine(y));
            for (int x = 0; x < hcmpW; x += 3) { hdiff += qAbs(qGray(a[x]) - qGray(b[x])); hn++; }
        }
        QFile hrf(outdir + "/longshot_wide_report.txt");
        if (hrf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&hrf);
            ts.setEncoding(QStringConverter::Utf8);
            ts << "frames=" << hframes << " matched=" << hmatched << " dir=" << hdir << "\\n";
            ts << "canvas=" << hcanvas.width() << "x" << hcanvas.height()
               << " source=" << wide.width() << "x" << wide.height() << "\\n";
            ts << "meanAbsDiff=" << (hn ? double(hdiff) / hn : -1) << "\\n";
            hrf.close();
        }"""
if anchor in s:
    s = s.replace(anchor, add, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("hselftest added")
else:
    print("MISS anchor")
