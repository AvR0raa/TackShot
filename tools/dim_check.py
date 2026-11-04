import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
old = """        QFile rf(outdir + "/select_report.txt");
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts << "during=" << during.width() << "x" << during.height() << "\\n";
            ts << "after=" << after.width() << "x" << after.height() << "\\n";
            rf.close();
        }"""
new = """        // 取样对比：选区内 vs 选区外的亮度（验证暗色遮罩是否生效）
        auto meanGray = [](const QImage& img, QRect r) -> double {
            if (img.isNull()) return -1;
            r = r.intersected(img.rect());
            if (r.isEmpty()) return -1;
            long long s = 0; int n = 0;
            for (int y = r.top(); y <= r.bottom(); y += 4)
                for (int x = r.left(); x <= r.right(); x += 4) {
                    s += qGray(img.pixel(x, y)); ++n;
                }
            return n ? double(s) / n : -1;
        };
        QRect insideRect(300, 220, 250, 150);     // 选区内
        QRect outsideRect(40, 40, 120, 120);      // 选区外（左上角）
        double inside = meanGray(during, insideRect);
        double outside = meanGray(during, outsideRect);

        QFile rf(outdir + "/select_report.txt");
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts << "during=" << during.width() << "x" << during.height() << "\\n";
            ts << "after=" << after.width() << "x" << after.height() << "\\n";
            ts << "insideGray=" << inside << " outsideGray=" << outside
               << " dimmed=" << ((outside < inside * 0.8) ? "true" : "false") << "\\n";
            rf.close();
        }"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("dim check added")
else:
    print("MISS")
