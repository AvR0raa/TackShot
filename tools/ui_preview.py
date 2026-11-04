import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
anchor = "    // 拖拽抖动自检"
code = r'''    // UI 预览：把工具条 / 设置窗 / 钉图窗渲染成 PNG，方便离线检查样式
    int uiIdx = args.indexOf("--ui-preview");
    if (uiIdx >= 0) {
        QString outdir = (uiIdx + 1 < args.size()) ? args[uiIdx + 1] : ".";
        QDir().mkpath(outdir);

        QImage base(1400, 860, QImage::Format_RGB32);
        {
            QPainter p(&base);
            QLinearGradient g(0, 0, base.width(), base.height());
            g.setColorAt(0, QColor("#2b3f63"));
            g.setColorAt(1, QColor("#16202e"));
            p.fillRect(base.rect(), g);
            p.setPen(QColor(255, 255, 255, 26));
            for (int x = 0; x < base.width(); x += 40) p.drawLine(x, 0, x, base.height());
            for (int y = 0; y < base.height(); y += 40) p.drawLine(0, y, base.width(), y);
            p.setPen(QColor(255, 255, 255, 60));
            QFont f; f.setPixelSize(30);
            p.setFont(f);
            p.drawText(80, 120, QStringLiteral("TackShot UI preview"));
            f.setPixelSize(16);
            p.setFont(f);
            p.drawText(80, 160, QStringLiteral("synthetic desktop for toolbar rendering"));
        }

        auto* ov = new Overlay(base, QRect(0, 0, 1400, 860), 1.0);
        ov->demoSetup();
        ov->show();
        QCoreApplication::processEvents();
        QThread::msleep(250);
        QCoreApplication::processEvents();

        QImage full = ov->grab().toImage();
        full.save(outdir + "/overlay_full.png");

        // 工具条单独截图
        for (QWidget* w : ov->findChildren<QWidget*>()) {
            if (w->objectName() == "toolbar") {
                QImage bar = w->grab().toImage();
                bar.save(outdir + "/toolbar.png");
                break;
            }
        }

        {
            SettingsDialog dlg(nullptr);
            dlg.show();
            QCoreApplication::processEvents();
            QThread::msleep(150);
            QCoreApplication::processEvents();
            dlg.grab().toImage().save(outdir + "/settings.png");
        }
        ov->hide();
        ov->deleteLater();
        return 0;
    }

'''
if anchor in s:
    s = s.replace(anchor, code + anchor, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("ui preview mode added")
else:
    print("MISS")
