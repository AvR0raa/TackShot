import io

# 版本号 1.6.1
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\common.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace('#define APP_VERSION "1.0.0"', '#define APP_VERSION "1.6.1"')
io.open(p, "w", encoding="utf-8").write(s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\res\app.rc"
s = io.open(p, encoding="utf-8").read()
s = s.replace("FILEVERSION 1,6,0,0", "FILEVERSION 1,6,1,0").replace("PRODUCTVERSION 1,6,0,0", "PRODUCTVERSION 1,6,1,0")
s = s.replace('VALUE "FileVersion", "1.6.0.0"', 'VALUE "FileVersion", "1.6.1.0"')
s = s.replace('VALUE "ProductVersion", "1.6.0.0"', 'VALUE "ProductVersion", "1.6.1.0"')
io.open(p, "w", encoding="utf-8").write(s)

# 长截图 v2 自检
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
if "--longshot2-selftest" not in s:
    anchor = "    // 纯抓屏诊断"
    code = r'''    // 长截图（竖向 + 回滚忽略）自检
    int ls2 = args.indexOf("--longshot2-selftest");
    if (ls2 >= 0) {
        QString out = (ls2 + 1 < args.size()) ? args[ls2 + 1] : "ls2.txt";
        const int W = 800, H = 3000, FH = 600;
        QImage page(W, H, QImage::Format_RGB32);
        {
            QPainter p(&page);
            QLinearGradient g(0, 0, 0, H);
            g.setColorAt(0, QColor("#1b2a3a"));
            g.setColorAt(1, QColor("#7fa8c9"));
            p.fillRect(page.rect(), g);
            for (int y = 0; y < H; y += 37) {
                p.setPen(QColor(255, 255, 255, 40 + (y * 7) % 120));
                p.drawLine(0, y, W, y);
            }
            for (int i = 0; i < 60; ++i) {
                const int y = (i * 47) % (H - 40);
                p.fillRect(QRect((i * 91) % (W - 120), y, 120, 26), QColor::fromHsv((i * 37) % 360, 180, 220));
            }
        }

        auto frameAt = [&](int y) { return page.copy(0, qBound(0, y, H - FH), W, FH); };

        QStringList log;
        bool pass = true;

        // 1) 向下滚动 3 次（每次 300px）：应竖向拼接
        QImage canvas = frameAt(0);
        QImage prev = canvas;
        int appends = 0;
        for (int step = 1; step <= 3; ++step) {
            const QImage f = frameAt(step * 300);
            const int dy = longshot::verticalShift(prev, f);
            bool matched = false;
            if (dy != INT_MIN && dy <= 1) {
                log << QString("step%1: 忽略(回滚/未动) dy=%2").arg(step).arg(dy);
            } else {
                QImage next = longshot::appendFrame(canvas, f, &matched);
                if (matched) { canvas = next; ++appends; }
            }
            prev = f;
            log << QString("step%1: dy=%2 matched=%3 canvas=%4x%5")
                       .arg(step).arg(dy).arg(matched).arg(canvas.width()).arg(canvas.height());
        }
        const bool verticalOk = (canvas.width() == W) && (canvas.height() == FH + 3 * 300);
        pass &= verticalOk;
        log << QString("vertical: width=%1 height=%2 expect=%3 pass=%4")
                   .arg(canvas.width()).arg(canvas.height()).arg(FH + 3 * 300).arg(verticalOk);

        // 2) 拼出来的内容必须和原页面逐像素一致
        QImage expect = page.copy(0, 0, W, FH + 3 * 300);
        long long diff = 0;
        int maxd = 0;
        for (int y = 0; y < expect.height(); ++y) {
            const QRgb* a = reinterpret_cast<const QRgb*>(expect.constScanLine(y));
            const QRgb* b = reinterpret_cast<const QRgb*>(canvas.constScanLine(y));
            for (int x = 0; x < W; x += 3) {
                const int d = std::abs(qGray(a[x]) - qGray(b[x]));
                diff += d;
                maxd = std::max(maxd, d);
            }
        }
        const bool pixelOk = (maxd <= 2);
        pass &= pixelOk;
        log << QString("pixels: maxGrayDiff=%1 pass=%2").arg(maxd).arg(pixelOk);

        // 3) 回滚：向上滚 300px 应被判定为负位移
        const QImage back = frameAt(3 * 300 - 300);
        const int dyBack = longshot::verticalShift(prev, back);
        const bool rollbackOk = (dyBack != INT_MIN && dyBack < 0);
        pass &= rollbackOk;
        log << QString("rollback: dy=%1 (expect <0) pass=%2").arg(dyBack).arg(rollbackOk);

        log << QString("ALL_PASS=%1").arg(pass ? "true" : "false");
        QFile f(out);
        if (f.open(QIODevice::WriteOnly)) {
            QTextStream ts(&f);
            ts.setEncoding(QStringConverter::Utf8);
            for (const QString& l : log) ts << l << "\n";
            f.close();
        }
        return pass ? 0 : 23;
    }

'''
    if anchor in s:
        s = s.replace(anchor, code + anchor, 1)
        io.open(p, "w", encoding="utf-8").write(s)
print("version 1.6.1 + longshot2 selftest")
