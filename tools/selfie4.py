import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
old = """        QImage selfie;
        if (target) selfie = target->grabWindow(0).toImage();
        if (selfie.isNull()) selfie = capture::captureRect(rect);
        bool saved = selfie.save(outPng);"""
new = """        QImage selfie;
        if (target) selfie = target->grabWindow(0).toImage();
        if (selfie.isNull()) selfie = capture::captureRect(rect);
        bool saved = selfie.save(outPng);

        QImage widgetPic = ov->grab().toImage();
        QRect winPhys = capture::nativeWindowRect(quintptr(ov->winId()));
        QRect monPhys = capture::nativeMonitorRect(quintptr(ov->winId()));"""
if old in s:
    s = s.replace(old, new, 1)
    s = s.replace("""                        .arg(dpr).arg(selfie.width()).arg(selfie.height()).arg(saved ? "true" : "false")
                        .toUtf8());""",
"""                        .arg(dpr).arg(selfie.width()).arg(selfie.height()).arg(saved ? "true" : "false")
                        .toUtf8());
            f.write(QString("widget=%1x%2 widgetDpr=%3 widgetGrab=%4x%5 winPhys=%6,%7 %8x%9 monPhys=%10,%11 %12x%13\\n")
                        .arg(ov->width()).arg(ov->height()).arg(ov->devicePixelRatioF())
                        .arg(widgetPic.width()).arg(widgetPic.height())
                        .arg(winPhys.x()).arg(winPhys.y()).arg(winPhys.width()).arg(winPhys.height())
                        .arg(monPhys.x()).arg(monPhys.y()).arg(monPhys.width()).arg(monPhys.height())
                        .toUtf8());""")
    io.open(p, "w", encoding="utf-8").write(s)
    print("selfie diagnostics extended")
else:
    print("MISS")
