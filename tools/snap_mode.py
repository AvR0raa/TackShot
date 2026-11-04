import io

# 在 captureVirtualDesktop 里记录路径
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\capture.cpp"
s = io.open(p, encoding="utf-8").read()
if 'g_lastPath = QStringLiteral("dxgi")' not in s:
    # DXGI 成功返回处
    s = s.replace("    return img;", "    g_lastPath = QStringLiteral(\"dxgi\");\n    return img;", 1)
    # GDI 兜底
    s = s.replace("QImage captureWithQt(QRect* physicalRectOut) {",
                  "QImage captureWithQt(QRect* physicalRectOut) {\n    g_lastPath = QStringLiteral(\"gdi\");", 1)
io.open(p, "w", encoding="utf-8").write(s)

# main.cpp：--snap
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
anchor = "    // 覆盖层自拍"
code = r'''    // 纯抓屏诊断：抓一张桌面存盘，并报告路径/DPI 状态/黑边情况
    int snapIdx = args.indexOf("--snap");
    if (snapIdx >= 0) {
        QString outPng = (snapIdx + 1 < args.size()) ? args[snapIdx + 1] : "snap.png";
        QString err;
        QRect rect;
        QImage img = capture::captureVirtualDesktop(&rect, &err);
        bool saved = !img.isNull() && img.save(outPng);

        auto mean = [&img](QRect r) -> double {
            if (img.isNull()) return -1;
            r = r.intersected(img.rect());
            if (r.isEmpty()) return -1;
            long long s = 0; int n = 0;
            for (int y = r.top(); y <= r.bottom(); y += 4)
                for (int x = r.left(); x <= r.right(); x += 4) { s += qGray(img.pixel(x, y)); ++n; }
            return n ? double(s) / n : -1;
        };
        QString info = QString("path=%1 err=%2 img=%3x%4 physRect=%5,%6 %7x%8 saved=%9\n")
                           .arg(capture::lastPath(), err)
                           .arg(img.width()).arg(img.height())
                           .arg(rect.x()).arg(rect.y()).arg(rect.width()).arg(rect.height())
                           .arg(saved ? "true" : "false");
        if (!img.isNull()) {
            info += QString("left=%1 right=%2 bottom=%3\n")
                        .arg(mean(QRect(0, 0, img.width() / 2, img.height())))
                        .arg(mean(QRect(int(img.width() * 0.85), 0, img.width() / 10, img.height())))
                        .arg(mean(QRect(0, int(img.height() * 0.85), img.width(), img.height() / 10)));
            // 逐列找“内容右边界”
            int contentRight = img.width();
            for (int x = img.width() - 1; x >= 0; x -= 2) {
                bool nonBlack = false;
                for (int y = 0; y < img.height(); y += 16)
                    if (qGray(img.pixel(x, y)) > 8) { nonBlack = true; break; }
                if (nonBlack) { contentRight = x; break; }
            }
            int contentBottom = img.height();
            for (int y = img.height() - 1; y >= 0; y -= 2) {
                bool nonBlack = false;
                for (int x = 0; x < img.width(); x += 16)
                    if (qGray(img.pixel(x, y)) > 8) { nonBlack = true; break; }
                if (nonBlack) { contentBottom = y; break; }
            }
            info += QString("contentRight=%1 contentBottom=%2\n").arg(contentRight).arg(contentBottom);
        }
        info += "dpi: " + capture::dpiAwarenessInfo() + "\n";

        QFile f(outPng + ".txt");
        if (f.open(QIODevice::WriteOnly)) { f.write(info.toUtf8()); f.close(); }
        return 0;
    }

'''
if anchor in s:
    s = s.replace(anchor, code + anchor, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("snap mode added")
else:
    print("MISS")
