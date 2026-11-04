import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()

start = s.index("    g_tray = new QSystemTrayIcon(icon, &app);")
end = s.index("    g_tray->setContextMenu(menu);")
new = r'''    g_tray = new QSystemTrayIcon(icon, &app);

    // ---- 托盘菜单图标（现画，不依赖图片资源）----
    auto trayPix = [](const std::function<void(QPainter&)>& draw) {
        QPixmap pm(32, 32);
        pm.fill(Qt::transparent);
        pm.setDevicePixelRatio(2);
        QPainter p(&pm);
        p.setRenderHint(QPainter::Antialiasing, true);
        p.setPen(QPen(Theme::p().text, 1.6, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
        p.setBrush(Qt::NoBrush);
        draw(p);
        p.end();
        return QIcon(pm);
    };
    auto iconShot = trayPix([](QPainter& p) {
        p.drawRoundedRect(QRectF(3, 6, 14, 10), 2, 2);
        p.drawEllipse(QPointF(10, 11), 2.6, 2.6);
        p.drawLine(QPointF(6.5, 6), QPointF(7.5, 4));
        p.drawLine(QPointF(7.5, 4), QPointF(12.5, 4));
        p.drawLine(QPointF(12.5, 4), QPointF(13.5, 6));
    });
    auto iconLong = trayPix([](QPainter& p) {
        p.drawRoundedRect(QRectF(4, 3, 12, 8), 2, 2);
        p.drawLine(QPointF(10, 12), QPointF(10, 17));
        p.drawLine(QPointF(7, 14.5), QPointF(10, 17.5));
        p.drawLine(QPointF(13, 14.5), QPointF(10, 17.5));
    });
    auto iconRec = trayPix([](QPainter& p) {
        p.setBrush(Theme::p().danger);
        p.setPen(Qt::NoPen);
        p.drawEllipse(QPointF(10, 10), 5, 5);
    });
    auto iconGif = trayPix([](QPainter& p) {
        p.drawRoundedRect(QRectF(3, 4, 14, 12), 2, 2);
        QFont f; f.setPixelSize(7); f.setBold(true);
        p.setFont(f);
        p.drawText(QRectF(3, 4, 14, 12), Qt::AlignCenter, QStringLiteral("GIF"));
    });
    auto iconMp4 = trayPix([](QPainter& p) {
        p.drawRoundedRect(QRectF(3, 4, 14, 12), 2, 2);
        QFont f; f.setPixelSize(7); f.setBold(true);
        p.setFont(f);
        p.drawText(QRectF(3, 4, 14, 12), Qt::AlignCenter, QStringLiteral("MP4"));
    });
    auto iconGear = trayPix([](QPainter& p) {
        p.drawEllipse(QPointF(10, 10), 2.6, 2.6);
        p.drawEllipse(QPointF(10, 10), 6.2, 6.2);
        for (int i = 0; i < 6; ++i) {
            const qreal a = i * M_PI / 3.0;
            p.drawLine(QPointF(10 + std::cos(a) * 6.0, 10 + std::sin(a) * 6.0),
                       QPointF(10 + std::cos(a) * 7.8, 10 + std::sin(a) * 7.8));
        }
    });
    auto iconFolder = trayPix([](QPainter& p) {
        QPainterPath path;
        path.moveTo(3, 6);
        path.lineTo(8, 6);
        path.lineTo(9.5, 8);
        path.lineTo(17, 8);
        path.lineTo(17, 15);
        path.lineTo(3, 15);
        path.closeSubpath();
        p.drawPath(path);
    });
    auto iconInfo = trayPix([](QPainter& p) {
        p.drawEllipse(QPointF(10, 10), 6.5, 6.5);
        QFont f; f.setPixelSize(9); f.setBold(true);
        p.setFont(f);
        p.drawText(QRectF(3, 3, 14, 14), Qt::AlignCenter, QStringLiteral("i"));
    });
    auto iconPower = trayPix([](QPainter& p) {
        p.drawArc(QRectF(4, 4.5, 12, 12), 40 * 16, 280 * 16);
        p.drawLine(QPointF(10, 2.5), QPointF(10, 8));
    });

    auto* menu = new QMenu;
    auto addItem = [&](const QIcon& ic, const QString& text, const QKeySequence& seq,
                       std::function<void()> fn) {
        auto* act = menu->addAction(ic, text);
        if (!seq.isEmpty()) {
            act->setShortcut(seq);
            act->setShortcutContext(Qt::WidgetShortcut);
            act->setShortcutVisibleInContextMenu(true);
        }
        QObject::connect(act, &QAction::triggered, menu, [fn]() { fn(); });
        return act;
    };

    QKeySequence hotkeySeq(Config::get().hotkeyMods, Qt::KeyboardKey(Config::get().hotkeyVk));
    auto* actCapture = addItem(iconShot, QStringLiteral("截图"), hotkeySeq, []() { doCapture(); });

    auto* recMenu = menu->addMenu(iconRec, QStringLiteral("录制"));
    recMenu->addAction(iconGif, QStringLiteral("录制为 GIF"), []() {
        Config::get().recordFormat = "gif";
        Config::get().save();
        doCapture();
    });
    recMenu->addAction(iconMp4, QStringLiteral("录制为 MP4"), []() {
        Config::get().recordFormat = "mp4";
        Config::get().save();
        doCapture();
    });

    addItem(iconGear, QStringLiteral("设置…"), QKeySequence("Ctrl+,"), []() {
        SettingsDialog dlg;
        dlg.exec();
    });
    addItem(iconFolder, QStringLiteral("打开保存目录"), QKeySequence(), []() {
        QString d = Config::get().saveDir;
        QDir().mkpath(d);
        QDesktopServices::openUrl(QUrl::fromLocalFile(d));
    });
    menu->addSeparator();
    addItem(iconInfo, QStringLiteral("关于"), QKeySequence(), []() {
        QMessageBox::about(nullptr, QStringLiteral("关于 TackShot"),
            QString("<b>TackShot</b> %1<br>%2<br><br>"
                    "本地截图 / 标注 / 贴图工具（默认不联网）<br>"
                    "翻译功能需自行配置 API Key。").arg(APP_VERSION, TS_APP_NAME_CN));
    });
    addItem(iconPower, QStringLiteral("退出"), QKeySequence(), []() { qApp->quit(); });

    // 配置变化（设置窗即时生效）→ 重新注册热键、更新菜单文字
    QObject::connect(&Config::get(), &Config::changed, menu, [actCapture, menu]() {
        if (g_hotkey) g_hotkey->install(Config::get().hotkeyMods, Config::get().hotkeyVk);
        actCapture->setText(QStringLiteral("截图"));
        actCapture->setShortcut(QKeySequence(Config::get().hotkeyMods,
                                             Qt::KeyboardKey(Config::get().hotkeyVk)));
        actCapture->setShortcutVisibleInContextMenu(true);
        menu->update();
    });

'''
s = s[:start] + new + s[end:]
s = s.replace('#include "theme.h"', '#include "theme.h"\n#include <functional>')
io.open(p, "w", encoding="utf-8").write(s)
print("tray menu rewritten")
