import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
old = """        QFile f(out);
        if (f.open(QIODevice::WriteOnly)) { f.write(info.toUtf8()); f.close(); }
        ov->hide();
        return 0;"""
new = """        // 抓窗口实际显示出来的内容，检查右/下是否黑边（backing store 与窗口尺寸不一致的典型症状）
        QImage cap = sc->grabWindow(WId(ov->winId())).toImage();
        if (!cap.isNull()) {
            auto mean = [&cap](QRect r) -> double {
                r = r.intersected(cap.rect());
                if (r.isEmpty()) return -1;
                long long sum = 0; int n = 0;
                for (int y = r.top(); y <= r.bottom(); y += 4)
                    for (int x = r.left(); x <= r.right(); x += 4) { sum += qGray(cap.pixel(x, y)); ++n; }
                return n ? double(sum) / n : -1;
            };
            double left = mean(QRect(0, 0, cap.width() / 2, cap.height()));
            double right = mean(QRect(int(cap.width() * 0.85), 0, cap.width() / 10, cap.height()));
            double bottom = mean(QRect(0, int(cap.height() * 0.85), cap.width(), cap.height() / 10));
            info += QString("grabSize=%1x%2 leftGray=%3 rightGray=%4 bottomGray=%5\\n")
                        .arg(cap.width()).arg(cap.height()).arg(left).arg(right).arg(bottom);
            cap.save(out + ".png");
        }
        QFile f(out);
        if (f.open(QIODevice::WriteOnly)) { f.write(info.toUtf8()); f.close(); }
        ov->hide();
        return 0;"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("grab check added")
else:
    print("MISS")
