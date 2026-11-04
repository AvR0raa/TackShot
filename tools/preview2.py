import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()

s = s.replace("""        QString outdir = (uiIdx + 1 < args.size()) ? args[uiIdx + 1] : ".";
        QDir().mkpath(outdir);""",
"""        QString outdir = (uiIdx + 1 < args.size()) ? args[uiIdx + 1] : ".";
        QDir().mkpath(outdir);
        if (args.contains("--theme-light")) Theme::setMode(Theme::Light, false);
        if (args.contains("--theme-dark")) Theme::setMode(Theme::Dark, false);""")

s = s.replace("""        {
            SettingsDialog dlg(nullptr);
            dlg.show();
            QCoreApplication::processEvents();
            QThread::msleep(150);
            QCoreApplication::processEvents();
            dlg.grab().toImage().save(outdir + "/settings.png");
        }""",
"""        {
            SettingsDialog dlg(nullptr);
            dlg.show();
            QCoreApplication::processEvents();
            QThread::msleep(200);
            QCoreApplication::processEvents();
            dlg.grab().toImage().save(outdir + "/settings.png");
        }

        {
            QImage pinImg(520, 300, QImage::Format_RGB32);
            {
                QPainter p(&pinImg);
                QLinearGradient g(0, 0, 520, 300);
                g.setColorAt(0, QColor("#3a6ea5"));
                g.setColorAt(1, QColor("#7fb2d9"));
                p.fillRect(pinImg.rect(), g);
                p.setPen(Qt::white);
                QFont f; f.setPixelSize(22); f.setBold(true);
                p.setFont(f);
                p.drawText(QRect(0, 0, 520, 300), Qt::AlignCenter, QStringLiteral("Pinned image"));
            }
            auto* pin = new PinWindow(pinImg);
            pin->placeAt(QPoint(60, 60));
            pin->show();
            QCoreApplication::processEvents();
            QThread::msleep(250);
            QCoreApplication::processEvents();
            pin->grab().toImage().save(outdir + "/pin.png");
            pin->close();
        }""")
io.open(p, "w", encoding="utf-8").write(s)
print("preview extended")
