import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
old = """        int frames = 0;
        QElapsedTimer t; t.start();
        while (t.elapsed() < seconds * 1000) {
            QRect virt;
            QImage full = capture::captureVirtualDesktop(&virt, nullptr);
            if (!full.isNull()) {
                QRect r = region.translated(-virt.topLeft()).intersected(QRect(0, 0, full.width(), full.height()));
                if (!r.isEmpty()) { rec.writeFrame(full.copy(r)); frames++; }
            }
            QThread::msleep(1000 / 15);
        }
        bool ok = rec.close();"""
new = """        int frames = 0;
        qint64 capMs = 0, encMs = 0;
        QElapsedTimer t; t.start();
        while (t.elapsed() < seconds * 1000) {
            QElapsedTimer s1; s1.start();
            QImage part = capture::captureRect(region);
            capMs += s1.elapsed();
            if (part.isNull()) {
                QRect virt;
                QImage full = capture::captureVirtualDesktop(&virt, nullptr);
                if (!full.isNull()) {
                    QRect r = region.translated(-virt.topLeft()).intersected(QRect(0, 0, full.width(), full.height()));
                    if (!r.isEmpty()) part = full.copy(r);
                }
            }
            if (!part.isNull()) {
                QElapsedTimer s2; s2.start();
                rec.writeFrame(part);
                encMs += s2.elapsed();
                frames++;
            }
            QThread::msleep(1000 / 15);
        }
        bool ok = rec.close();"""
if old in s:
    s = s.replace(old, new, 1)
s = s.replace('ts << "ok=" << (ok ? "true" : "false") << " frames=" << frames',
              'ts << "ok=" << (ok ? "true" : "false") << " frames=" << frames\n               << " avgCapMs=" << (frames ? double(capMs)/frames : -1)\n               << " avgEncMs=" << (frames ? double(encMs)/frames : -1)')
io.open(p, "w", encoding="utf-8").write(s)
print("instrumented")
