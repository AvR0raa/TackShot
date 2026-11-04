import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
anchor = "    // 覆盖层 DPI 探针"
code = r'''    // 覆盖层自拍：把覆盖层显示出来，再用抓屏把「屏幕上真正显示的东西」存下来
    int sfIdx = args.indexOf("--overlay-selfie");
    if (sfIdx >= 0) {
        QString outPng = (sfIdx + 1 < args.size()) ? args[sfIdx + 1] : "selfie.png";
        QString err;
        QRect rect;
        QImage shot = capture::captureVirtualDesktop(&rect, &err);
        if (shot.isNull()) return 18;
        qreal dpr = 1.0;
        if (QScreen* s = QGuiApplication::primaryScreen()) dpr = s->devicePixelRatio();
        QScreen* target = QGuiApplication::screenAt(QCursor::pos());
        if (target) dpr = target->devicePixelRatio();
        QRect useRect = rect;
        QImage useShot = shot;
        if (target) {
            QRect phys(int(target->geometry().x() * target->devicePixelRatio()),
                       int(target->geometry().y() * target->devicePixelRatio()),
                       int(target->geometry().width() * target->devicePixelRatio()),
                       int(target->geometry().height() * target->devicePixelRatio()));
            QRect inShot(phys.topLeft() - rect.topLeft(), phys.size());
            if (shot.rect().contains(inShot)) {
                useShot = shot.copy(inShot);
                useRect = phys;
                dpr = target->devicePixelRatio();
            }
        }
        auto* ov = new Overlay(useShot, useRect, dpr);
        if (target) ov->setTargetScreen(target);
        ov->show();
        QCoreApplication::processEvents();
        QThread::msleep(600);
        QCoreApplication::processEvents();

        QImage selfie = capture::captureRect(rect);
        bool saved = selfie.save(outPng);

        QFile f(outPng + ".txt");
        if (f.open(QIODevice::WriteOnly)) {
            f.write(QString("shot=%1x%2 physRect=%3,%4 %5x%6 dpr=%7 selfie=%8x%9 saved=%10\n")
                        .arg(useShot.width()).arg(useShot.height())
                        .arg(useRect.x()).arg(useRect.y()).arg(useRect.width()).arg(useRect.height())
                        .arg(dpr).arg(selfie.width()).arg(selfie.height()).arg(saved ? "true" : "false")
                        .toUtf8());
            f.close();
        }
        ov->hide();
        return 0;
    }

'''
if anchor in s:
    s = s.replace(anchor, code + anchor, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("selfie mode added")
else:
    print("MISS")
