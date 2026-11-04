#include "common.h"
#include <QWindow>
#include "config.h"
#include "theme.h"
#include <functional>
#include <cmath>
#include <QPainterPath>
#include "hotkey.h"
#include "capture.h"
#include "overlay.h"
#include "pinwindow.h"
#include "settingsdialog.h"
#include "ocrline.h"
#include "ocrdialog.h"
#include "vision.h"
#include "baidu.h"
#include "simpletex.h"
#include "longshot.h"
#include "gifenc.h"
#include "mfrec.h"
#include "audiocap.h"
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <mferror.h>
#include "translate.h"
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QEventLoop>
#include <QJsonDocument>
#include <QJsonObject>
#include "secrets.h"
#include <windows.h>
#include <mmsystem.h>
#include <QThread>
#include <QElapsedTimer>
#include <QPainter>
#include <QTextStream>
#include <QFileInfo>

#include <QApplication>
#include <QSystemTrayIcon>
#include <QMenu>
#include <QAction>
#include <QPainter>
#include <QPainterPath>
#include <QTimer>
#include <QDir>
#include <QMessageBox>
#include <QIcon>
#include <QLocalServer>
#include <QLocalSocket>
#include <QStandardPaths>
#include <QDebug>
#include <QScreen>
#include <QClipboard>
#include <QDialog>
#include <QListWidget>
#include <QLabel>
#include <QSplitter>
#include <QPushButton>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFileDialog>
#include <QDateTime>
#include <QDesktopServices>
#include <QUrl>
#include <QCursor>
#include <QLinearGradient>
#include <cstdio>
#include <QFont>
#include <QtMath>
#include <QPixmap>

static QSystemTrayIcon* g_tray = nullptr;
static HotkeyManager*   g_hotkey = nullptr;
static Overlay*         g_overlay = nullptr;
static QVector<PinWindow*> g_pins;

static QRect screenPhysicalRect(QScreen* s) {
    const qreal d = s->devicePixelRatio();
    const QRect g = s->geometry();
    return QRect(QPoint(qRound(g.x() * d), qRound(g.y() * d)),
                 QSize(qRound(g.width() * d), qRound(g.height() * d)));
}

static QIcon makeAppIcon() {
    QPixmap pm(64, 64);
    pm.fill(Qt::transparent);
    QPainter p(&pm);
    p.setRenderHint(QPainter::Antialiasing);
    QLinearGradient g(0, 0, 64, 64);
    g.setColorAt(0, QColor("#3d7bfd"));
    g.setColorAt(1, QColor("#1f4fd0"));
    p.setBrush(g);
    p.setPen(Qt::NoPen);
    p.drawRoundedRect(QRectF(2, 2, 60, 60), 14, 14);
    p.setPen(QPen(Qt::white, 4, Qt::SolidLine, Qt::RoundCap));
    p.drawLine(20, 20, 44, 44);
    p.drawLine(44, 20, 20, 44);
    p.setBrush(Qt::white);
    p.drawEllipse(QPointF(32, 32), 7, 7);
    p.end();
    return QIcon(pm);
}

static void showOverlay(const QImage& shot, const QRect& rect, qreal dpr) {
    if (g_overlay) { g_overlay->close(); g_overlay = nullptr; }
    g_overlay = new Overlay(shot, rect, dpr);
    if (QScreen* sc = QGuiApplication::screenAt(QPoint(int(rect.center().x() / dpr),
                                                       int(rect.center().y() / dpr))))
        g_overlay->setTargetScreen(sc);
    QObject::connect(g_overlay, &Overlay::pinRequested, [](const QImage& img) {
        auto* w = new PinWindow(img);
        g_pins.append(w);
        QObject::connect(w, &QObject::destroyed, [](QObject* o) {
            g_pins.removeAll(static_cast<PinWindow*>(o));
        });
        QPoint cur = QCursor::pos();
        w->placeAt(cur + QPoint(16, 16));
        w->show();
        w->activateWindow();
    });
    QObject::connect(g_overlay, &Overlay::closed, []() { g_overlay = nullptr; });
    g_overlay->show();
    g_overlay->raise();
    g_overlay->activateWindow();
    g_overlay->setFocus();
}

static void captureLog(const QString& line) {
    QFile f(Config::get().dataDir() + "/capture.log");
    if (!f.open(QIODevice::Append)) return;
    f.write(QString("[%1] %2\n")
                .arg(QDateTime::currentDateTime().toString("MM-dd HH:mm:ss"), line).toUtf8());
    f.close();
}

static void doCapture() {
    QString err;
    QRect rect;
    QImage shot = capture::captureVirtualDesktop(&rect, &err);
    if (shot.isNull()) {
        if (g_tray) g_tray->showMessage(QStringLiteral("TackShot"), QStringLiteral("抓屏失败：%1").arg(err), QSystemTrayIcon::Critical, 4000);
        return;
    }
    qreal dpr = 1.0;
    if (QScreen* s = QGuiApplication::primaryScreen()) dpr = s->devicePixelRatio();

    // 混合 DPI：各屏缩放不同时，覆盖层只覆盖光标所在屏，避免整体缩放导致错位
    const auto screens = QGuiApplication::screens();
    bool mixed = false;
    for (QScreen* s : screens)
        if (!qFuzzyCompare(s->devicePixelRatio(), dpr)) { mixed = true; break; }
    if (mixed) {
        QScreen* cur = QGuiApplication::screenAt(QCursor::pos());
        if (!cur) cur = QGuiApplication::primaryScreen();
        if (cur) {
            const qreal sd = cur->devicePixelRatio();
            QRect phys = screenPhysicalRect(cur);
            QRect inShot = phys.translated(-rect.topLeft());
            if (shot.rect().contains(inShot) && inShot.width() > 16 && inShot.height() > 16) {
                shot = shot.copy(inShot);
                rect = phys;
                dpr = sd;
            }
        }
    }
    // 抓屏已经按物理像素取，正常不会有黑边；只有在确实检测到大片纯黑边框时才裁
    {
        QRect before = rect;
        QRect after = capture::trimBlackBorder(shot, rect);
        if (after.size() != before.size() &&
            after.width() >= before.width() * 0.9 && after.height() >= before.height() * 0.9) {
            rect = after;   // 只接受小范围修正，避免误裁黑壁纸
        }
    }
    {
        QString diag = QString("cursor=%1,%2 screens=")
                           .arg(QCursor::pos().x()).arg(QCursor::pos().y());
        for (QScreen* sc : screens)
            diag += QString("[%1 %2,%3 %4x%5 dpr=%6]")
                        .arg(sc->name()).arg(sc->geometry().x()).arg(sc->geometry().y())
                        .arg(sc->geometry().width()).arg(sc->geometry().height())
                        .arg(sc->devicePixelRatio());
        diag += QString(" mixed=%1 shot=%2x%3 physRect=%4,%5 %6x%7 dpr=%8")
                    .arg(mixed ? 1 : 0).arg(shot.width()).arg(shot.height())
                    .arg(rect.x()).arg(rect.y()).arg(rect.width()).arg(rect.height()).arg(dpr);
        captureLog(diag);
    }
    showOverlay(shot, rect, dpr);
}

int main(int argc, char** argv) {
    // 有些宿主（IDE/沙箱/启动器）会注入 QT_SCALE_FACTOR 之类的变量，
    // 它们会让 Qt 把 125% 的屏幕按 100% 渲染，导致截图覆盖层只铺满 80% 屏幕。
    // 我们始终按系统 DPI 工作，所以启动前清掉这些覆盖项。
    qunsetenv("QT_SCALE_FACTOR");
    qunsetenv("QT_SCALE_FACTOR_ROUNDING_POLICY");
    qunsetenv("QT_AUTO_SCREEN_SCALE_FACTOR");
    qputenv("QT_ENABLE_HIGHDPI_SCALING", "1");

    QApplication::setHighDpiScaleFactorRoundingPolicy(Qt::HighDpiScaleFactorRoundingPolicy::PassThrough);
    QApplication app(argc, argv);
    Theme::initFromConfig();
    Theme::applyGlobal();
    QApplication::setApplicationName(TS_APP_NAME);
    QApplication::setApplicationVersion(APP_VERSION);
    QApplication::setOrganizationName(TS_APP_NAME);
    QApplication::setQuitOnLastWindowClosed(false);

    QStringList args = app.arguments();

    // 密钥存储自检：DPAPI 加密写入 -> 读回 -> 删除
    int secIdx = args.indexOf("--secret-selftest");
    if (secIdx >= 0) {
        QString out = (secIdx + 1 < args.size()) ? args[secIdx + 1] : "secret.txt";
        const QString probeName = "selftest_probe";
        const QString value = QStringLiteral("sk-测试-1234567890");
        bool saved = secrets::save(probeName, value);
        QString back = secrets::load(probeName);
        bool same = (back == value);
        QFile f(secrets::storePath());
        bool exists = f.exists();
        QByteArray raw;
        if (f.open(QIODevice::ReadOnly)) { raw = f.readAll(); f.close(); }
        bool plainVisible = raw.contains(value.toUtf8());
        secrets::remove(probeName);

        bool pass = saved && same && exists && !plainVisible;
        QFile rf(out);
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts.setEncoding(QStringConverter::Utf8);
            ts << "saved=" << saved << " roundtrip=" << same
               << " plaintextInFile=" << plainVisible << "\n";
            ts << "storeSize=" << raw.size() << " pass=" << (pass ? "true" : "false") << "\n";
            rf.close();
        }
        return pass ? 0 : 14;
    }

    // UI 预览：把工具条 / 设置窗 / 钉图窗渲染成 PNG，方便离线检查样式
    int uiIdx = args.indexOf("--ui-preview");
    if (uiIdx >= 0) {
        QString outdir = (uiIdx + 1 < args.size()) ? args[uiIdx + 1] : ".";
        QDir().mkpath(outdir);
        if (args.contains("--theme-light")) Theme::setMode(Theme::Light, false);
        if (args.contains("--theme-dark")) Theme::setMode(Theme::Dark, false);

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
            for (int i = 0; i < 12; ++i) {
                QCoreApplication::processEvents();
                QThread::msleep(30);
            }
            pin->demoShowChrome();
            QCoreApplication::processEvents();
            pin->grab().toImage().save(outdir + "/pin.png");
            pin->close();
        }
        ov->hide();
        ov->deleteLater();
        return 0;
    }

    // 拖拽抖动自检：按 1px 步进拖 40 次，检查选区是否单调、无回跳
    int dgIdx = args.indexOf("--drag-selftest");
    if (dgIdx >= 0) {
        QString out = (dgIdx + 1 < args.size()) ? args[dgIdx + 1] : "drag.txt";
        QStringList log;
        bool allPass = true;

        for (qreal dpr : {1.0, 1.25, 1.5}) {
            QImage base(2000, 1400, QImage::Format_RGB32);
            base.fill(QColor("#203040"));
            auto* ov = new Overlay(base, QRect(0, 0, 2000, 1400), dpr);

            const QRect startSel(400, 300, 600, 400);
            ov->demoSelect(startSel);
            // 按下点必须落在“选区在控件里的位置”内：图像坐标 / dpr
            const QPoint press(qRound(startSel.center().x() / dpr),
                               qRound(startSel.center().y() / dpr));
            ov->demoSimPress(press);

            // 沿 x 拖 40 个逻辑像素
            const int steps = 40;
            int backSteps = 0, widthChanges = 0, prev = ov->demoSel().left();
            for (int i = 1; i <= steps; ++i) {
                ov->demoSimMove(QPoint(press.x() + i, press.y()));
                int x = ov->demoSel().left();
                if (x < prev) backSteps++;
                if (ov->demoSel().size() != startSel.size()) widthChanges++;
                prev = x;
            }

            QRect moved = ov->demoSel();
            // 期望：向左移动 steps 个逻辑像素（换算到图像坐标）
            const int expectedDx = qRound(steps * dpr);
            const int expectedLeft = startSel.left() + expectedDx;
            // 允许 ±2 的取整误差
            bool follows = qAbs(moved.left() - expectedLeft) <= 2;
            bool sizeKept = moved.size() == startSel.size();
            bool noBack = (backSteps == 0);
            bool pass = follows && sizeKept && noBack;
            allPass &= pass;

            // ---- 缩放手柄：拖右下角，尺寸应按位移增长 ----
            bool resizePass = false;
            {
                QRect cur = ov->demoSel();   // 已移动后的选区
                QPoint br(qRound((cur.x() + cur.width() - 1) / dpr),
                          qRound((cur.y() + cur.height() - 1) / dpr));
                ov->demoSimPress(br);
                ov->demoSimMove(QPoint(br.x() + 30, br.y() + 20));
                QRect after = ov->demoSel();
                resizePass = (after.width() == cur.width() + qRound(30 * dpr)) ||
                             qAbs(after.width() - (cur.width() + qRound(30 * dpr))) <= 2;
                ov->demoSimRelease(QPoint(br.x() + 30, br.y() + 20));
                log << QString("  resize dpr=%1 %2x%3 -> %4x%5 pass=%6")
                           .arg(dpr).arg(cur.width()).arg(cur.height())
                           .arg(after.width()).arg(after.height())
                           .arg(resizePass ? "true" : "false");
            }
            pass = pass && resizePass;
            allPass &= resizePass;

            // ---- 标注拖动：画一个矩形，再整体拖走 ----
            bool annotPass = false;
            {
                // 必须在选区内画，否则会变成重新拉框
                QRect s0 = ov->demoSel();
                QPoint p0(qRound((s0.x() + 40) / dpr), qRound((s0.y() + 40) / dpr));
                QPoint p1(qRound((s0.x() + 240) / dpr), qRound((s0.y() + 160) / dpr));
                ov->demoSetTool(Tool::Rect);
                ov->demoSimPress(p0);
                ov->demoSimMove(p1);
                ov->demoSimRelease(p1);
                int n0 = ov->demoAnnotCount();
                ov->demoSetTool(Tool::Select);
                QPoint grip(qRound((s0.x() + 140) / dpr), qRound((s0.y() + 100) / dpr));
                ov->demoSimPress(grip);
                QRect before = QRect(0, 0, 0, 0);
                if (ov->demoAnnotCount() > 0) {
                    Annotation a0 = ov->demoAnnot(n0 - 1);
                    if (a0.pts.size() >= 2) before = QRectF(a0.pts[0], a0.pts[1]).toRect();
                }
                {
                    QPointF lc = ov->demoToLocal(grip);
                    log << QString("  annotPress dpr=%1 count=%2 selected=%3 grip=%4,%5 local=%6,%7 "
                                   "hit=%8 sel=%9,%10 %11x%12 annotBounds=%13,%14 %15x%16")
                               .arg(dpr).arg(ov->demoAnnotCount()).arg(ov->demoSelected())
                               .arg(grip.x()).arg(grip.y())
                               .arg(lc.x()).arg(lc.y()).arg(ov->demoHitTest(grip))
                               .arg(ov->demoSel().x()).arg(ov->demoSel().y())
                               .arg(ov->demoSel().width()).arg(ov->demoSel().height())
                               .arg(ov->demoAnnotBounds(0).x()).arg(ov->demoAnnotBounds(0).y())
                               .arg(ov->demoAnnotBounds(0).width()).arg(ov->demoAnnotBounds(0).height());
                }
                ov->demoSimMove(QPoint(grip.x() + 40, grip.y() + 30));
                ov->demoSimRelease(QPoint(grip.x() + 40, grip.y() + 30));
                QRect after(0, 0, 0, 0);
                if (ov->demoAnnotCount() > 0) {
                    Annotation a1 = ov->demoAnnot(n0 - 1);
                    if (a1.pts.size() >= 2) after = QRectF(a1.pts[0], a1.pts[1]).toRect();
                }
                annotPass = !before.isNull() && !after.isNull() &&
                            qAbs((after.x() - before.x()) - qRound(40 * dpr)) <= 3 &&
                            qAbs((after.y() - before.y()) - qRound(30 * dpr)) <= 3;
                log << QString("  annotMove dpr=%1 %2,%3 -> %4,%5 pass=%6")
                           .arg(dpr).arg(before.x()).arg(before.y())
                           .arg(after.x()).arg(after.y()).arg(annotPass ? "true" : "false");
            }
            pass = pass && annotPass;
            allPass &= annotPass;

            log << QString("dpr=%1 start=%2,%3 movedTo=%4,%5 expectedX=%6 dy=%7 sizeOk=%8 back=%9 pass=%10")
                       .arg(dpr).arg(startSel.x()).arg(startSel.y())
                       .arg(moved.x()).arg(moved.y()).arg(expectedLeft).arg(moved.y() - startSel.y())
                       .arg(sizeKept ? "yes" : "no").arg(backSteps).arg(pass ? "true" : "false");

            // 竖直方向也走一段
            ov->demoSimRelease(QPoint(press.x() + steps, press.y()));
            ov->deleteLater();
        }

        log << QString("ALL_PASS=%1").arg(allPass ? "true" : "false");
        QFile f(out);
        if (f.open(QIODevice::WriteOnly)) {
            QTextStream ts(&f);
            for (const QString& l : log) ts << l << "\n";
            f.close();
        }
        return allPass ? 0 : 19;
    }

    // 本地公式模型自检：给一张公式图，输出 LaTeX

    // 云端识别自检：百度图片翻译 + SimpleTex 公式（对着 mock 跑）
    int csIdx = args.indexOf("--cloud-selftest");
    if (csIdx >= 0) {
        QString out = (csIdx + 1 < args.size()) ? args[csIdx + 1] : "cloud.txt";
        QImage img(320, 160, QImage::Format_RGB32);
        img.fill(Qt::white);
        {
            QPainter p(&img);
            p.setPen(Qt::black);
            QFont f; f.setPixelSize(18); p.setFont(f);
            p.drawText(QRect(10, 20, 300, 30), Qt::AlignLeft, QStringLiteral("这是第一段"));
            p.drawText(QRect(10, 70, 300, 30), Qt::AlignLeft, QStringLiteral("第二段文字"));
        }
        QStringList log;
        bool pass = true;

        BaiduPictureTranslate bd;
        auto br = bd.translate(img, QStringLiteral("auto"), QStringLiteral("en"),
                               QStringLiteral("appid-test"), QStringLiteral("secret-test"), 1);
        bool p1 = br.ok && br.lines.size() == 2 &&
                  br.lines[0].dst.contains("first") && br.lines[0].rect.width() == 200 &&
                  !br.pasteImage.isNull();
        log << QString("baidu: ok=%1 lines=%2 rect0=%3,%4 %5x%6 paste=%7x%8 pass=%9")
                   .arg(br.ok).arg(br.lines.size())
                   .arg(br.lines.isEmpty() ? -1 : br.lines[0].rect.x())
                   .arg(br.lines.isEmpty() ? -1 : br.lines[0].rect.y())
                   .arg(br.lines.isEmpty() ? -1 : br.lines[0].rect.width())
                   .arg(br.lines.isEmpty() ? -1 : br.lines[0].rect.height())
                   .arg(br.pasteImage.width()).arg(br.pasteImage.height()).arg(p1);
        pass &= p1;

        SimpleTexClient st;
        auto sr = st.recognize(img, QStringLiteral("uat-test"), true);
        bool p2 = sr.ok && sr.latex.contains("a^{2}");
        log << QString("simpletex: ok=%1 latex=%2 conf=%3 pass=%4")
                   .arg(sr.ok).arg(sr.latex).arg(sr.confidence).arg(p2);
        pass &= p2;

        auto bad = st.recognize(img, QString(), true);
        bool p3 = !bad.ok && !bad.error.isEmpty();
        log << QString("simpletex-no-token: ok=%1 err=%2 pass=%3")
                   .arg(bad.ok).arg(bad.error.left(20)).arg(p3);
        pass &= p3;

        log << QString("ALL_PASS=%1").arg(pass ? "true" : "false");
        QFile f(out);
        if (f.open(QIODevice::WriteOnly)) {
            QTextStream ts(&f);
            ts.setEncoding(QStringConverter::Utf8);
            for (const QString &l : log) ts << l << "\n";
            f.close();
        }
        return pass ? 0 : 24;
    }

    // 在线视觉识别自检：跑 mock 服务器的三个端点
    int vsIdx = args.indexOf("--vision-selftest");
    if (vsIdx >= 0) {
        QString base = (vsIdx + 1 < args.size()) ? args[vsIdx + 1] : "http://127.0.0.1:8901/v1";
        QString out = (vsIdx + 2 < args.size()) ? args[vsIdx + 2] : "vs.txt";
        QImage img(240, 120, QImage::Format_RGB32);
        img.fill(Qt::white);
        {
            QPainter p(&img);
            p.setPen(Qt::black);
            QFont f; f.setPixelSize(20); p.setFont(f);
            p.drawText(QRect(0, 0, 240, 120), Qt::AlignCenter, QStringLiteral("Hello 123"));
        }
        VisionClient vc;
        QStringList log;
        bool allPass = true;

        auto r1 = vc.recognize(img, QStringLiteral("识别图片"), base + "/ok", "mock-vl", "sk-test");
        bool p1 = r1.ok && r1.text.contains("OK");
        log << QString("ok: ok=%1 text=%2 pass=%3").arg(r1.ok).arg(r1.text.left(20)).arg(p1);
        allPass &= p1;

        auto r2 = vc.recognize(img, QString(), base + "/bad", "mock-vl", "sk-bad");
        bool p2 = !r2.ok && (r2.httpStatus == 401 || r2.error.contains("401") || r2.error.contains("Key"));
        log << QString("auth401: ok=%1 status=%2 err=%3 pass=%4")
                   .arg(r2.ok).arg(r2.httpStatus).arg(r2.error.left(20)).arg(p2);
        allPass &= p2;

        auto r3 = vc.recognize(img, QString(), base + "/noretry", "mock-vl", "sk-test");
        bool p3 = !r3.ok;
        log << QString("forbidden: ok=%1 status=%2 pass=%3").arg(r3.ok).arg(r3.httpStatus).arg(p3);
        allPass &= p3;

        log << QString("ALL_PASS=%1").arg(allPass ? "true" : "false");
        QFile f(out);
        if (f.open(QIODevice::WriteOnly)) {
            QTextStream ts(&f);
            ts.setEncoding(QStringConverter::Utf8);
            for (const QString& l : log) ts << l << "\n";
            f.close();
        }
        return allPass ? 0 : 21;
    }

    // 识别结果对话框预览
    int odlgIdx = args.indexOf("--ocr-dialog-preview");
    if (odlgIdx >= 0) {
        QString outPng = (odlgIdx + 1 < args.size()) ? args[odlgIdx + 1] : "ocrdialog.png";
        QImage base(640, 320, QImage::Format_RGB32);
        {
            QPainter p(&base);
            QLinearGradient g(0, 0, 640, 320);
            g.setColorAt(0, QColor("#20303f"));
            g.setColorAt(1, QColor("#3b5066"));
            p.fillRect(base.rect(), g);
            p.setPen(QColor("#e8eaed"));
            QFont f; f.setPixelSize(22); p.setFont(f);
            p.drawText(QRect(30, 40, 580, 240), Qt::AlignLeft | Qt::TextWordWrap,
                       QStringLiteral("Chapter 1  Introduction\nE = mc^2 and the integral appears here.\n第三个测试行"));
        }
        QVector<OcrLine> lines;
        {
            OcrLine l; l.text = QStringLiteral("Chapter 1  Introduction"); l.score = 0.98f;
            l.box = QRect(30, 40, 420, 30); lines.append(l);
            l.text = QStringLiteral("E = mc^2 and the integral appears here."); l.score = 0.93f;
            l.box = QRect(30, 90, 520, 30); lines.append(l);
            l.text = QStringLiteral("第三个测试行"); l.score = 0.99f;
            l.box = QRect(30, 140, 200, 30); lines.append(l);
        }
        OcrDialogInput in;
        in.image = base;
        in.lines = lines;
        in.backend = QStringLiteral("本地 OCR");
        in.elapsedMs = 860;
        OcrDialog dlg(in);
        dlg.setSourceLang(QStringLiteral("English"));
        dlg.setTargetLang(QStringLiteral("简体中文"));
        QStringList ids;
        for (const auto& p : TranslateClient::presets()) ids << p.id;
        dlg.setModels(ids, QStringLiteral("deepseek"));
        dlg.show();
        QCoreApplication::processEvents();
        QThread::msleep(200);
        QCoreApplication::processEvents();
        dlg.grab().toImage().save(outPng);
        dlg.close();
        return 0;
    }

    // 长截图（竖向 + 回滚忽略）自检
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

    // 纯抓屏诊断：抓一张桌面存盘，并报告路径/DPI 状态/黑边情况
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
        if (!img.isNull()) {
            // 对左半屏做去黑边测试
            QImage leftHalf = img.copy(QRect(0, 0, img.width() / 2, img.height()));
            QRect before(0, 0, leftHalf.width(), leftHalf.height());
            QRect after = capture::trimBlackBorder(leftHalf, before);
            info += QString("leftHalf before=%1x%2 after=%3x%4\n")
                        .arg(before.width()).arg(before.height())
                        .arg(after.width()).arg(after.height());
            leftHalf.save(outPng + ".left.png");
        }
        info += "dpi: " + capture::dpiAwarenessInfo() + "\n";

        QFile f(outPng + ".txt");
        if (f.open(QIODevice::WriteOnly)) { f.write(info.toUtf8()); f.close(); }
        return 0;
    }

    // 覆盖层自拍：把覆盖层显示出来，再用抓屏把「屏幕上真正显示的东西」存下来
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
        ov->setWindowOpacity(1.0);   // 自拍时跳过淡入动画，确保内容真的画出来
        QCoreApplication::processEvents();
        QThread::msleep(600);
        QCoreApplication::processEvents();

        QImage selfie;
        if (target) selfie = target->grabWindow(0).toImage();
        if (selfie.isNull()) selfie = capture::captureRect(rect);
        bool saved = selfie.save(outPng);

        QImage widgetPic = ov->grab().toImage();
        QRect winPhys = capture::nativeWindowRect(quintptr(ov->winId()));
        QRect monPhys = capture::nativeMonitorRect(quintptr(ov->winId()));

        QFile f(outPng + ".txt");
        if (f.open(QIODevice::WriteOnly)) {
            f.write(QString("shot=%1x%2 physRect=%3,%4 %5x%6 dpr=%7 selfie=%8x%9 saved=%10\n")
                        .arg(useShot.width()).arg(useShot.height())
                        .arg(useRect.x()).arg(useRect.y()).arg(useRect.width()).arg(useRect.height())
                        .arg(dpr).arg(selfie.width()).arg(selfie.height()).arg(saved ? "true" : "false")
                        .toUtf8());
            f.write(QString("widget=%1x%2 widgetDpr=%3 widgetGrab=%4x%5 winPhys=%6,%7 %8x%9 monPhys=%10,%11 %12x%13\n")
                        .arg(ov->width()).arg(ov->height()).arg(ov->devicePixelRatioF())
                        .arg(widgetPic.width()).arg(widgetPic.height())
                        .arg(winPhys.x()).arg(winPhys.y()).arg(winPhys.width()).arg(winPhys.height())
                        .arg(monPhys.x()).arg(monPhys.y()).arg(monPhys.width()).arg(monPhys.height())
                        .toUtf8());
            f.close();
        }
        ov->hide();
        return 0;
    }

    // 覆盖层 DPI 探针：真实创建一次覆盖层，记录窗口实际 DPR 与几何
    int dpIdx = args.indexOf("--overlay-dpi-probe");
    if (dpIdx >= 0) {
        QString out = (dpIdx + 1 < args.size()) ? args[dpIdx + 1] : "probe.txt";
        QScreen* sc = QGuiApplication::primaryScreen();
        qreal dpr = sc->devicePixelRatio();
        QRect phys(int(sc->geometry().x() * dpr), int(sc->geometry().y() * dpr),
                   int(sc->geometry().width() * dpr), int(sc->geometry().height() * dpr));
        QImage shot(phys.size(), QImage::Format_RGB32);
        shot.fill(QColor("#3355aa"));
        auto* ov = new Overlay(shot, phys, dpr);
        ov->setTargetScreen(sc);
        ov->show();
        QCoreApplication::processEvents();
        QThread::msleep(200);
        QCoreApplication::processEvents();

        QRect wr = capture::nativeWindowRect(quintptr(ov->winId()));
        QWindow* h = ov->windowHandle();

        QString info = QString("screen=%1 screenDpr=%2 screenGeom=%3,%4 %5x%6\n"
                               "physRect=%7,%8 %9x%10\n"
                               "widgetGeom=%11,%12 %13x%14 widgetDpr=%15\n"
                               "windowDpr=%16\n"
                               "win32Rect=%17,%18 %19x%20\n")
                           .arg(sc->name()).arg(dpr)
                           .arg(sc->geometry().x()).arg(sc->geometry().y())
                           .arg(sc->geometry().width()).arg(sc->geometry().height())
                           .arg(phys.x()).arg(phys.y()).arg(phys.width()).arg(phys.height())
                           .arg(ov->x()).arg(ov->y()).arg(ov->width()).arg(ov->height())
                           .arg(ov->devicePixelRatioF())
                           .arg(h ? h->devicePixelRatio() : -1.0)
                           .arg(wr.x()).arg(wr.y()).arg(wr.width()).arg(wr.height());
        // 抓窗口实际显示出来的内容，检查右/下是否黑边（backing store 与窗口尺寸不一致的典型症状）
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
            info += QString("grabSize=%1x%2 leftGray=%3 rightGray=%4 bottomGray=%5\n")
                        .arg(cap.width()).arg(cap.height()).arg(left).arg(right).arg(bottom);
            cap.save(out + ".png");
        }
        QFile f(out);
        if (f.open(QIODevice::WriteOnly)) { f.write(info.toUtf8()); f.close(); }
        ov->hide();
        return 0;
    }

    // 拉框实时性自检：按下+移动（不松开）时就应该能看到选区
    int ssIdx = args.indexOf("--select-selftest");
    if (ssIdx >= 0) {
        QString outdir = (ssIdx + 1 < args.size()) ? args[ssIdx + 1] : ".";
        QDir().mkpath(outdir);
        QImage base(1000, 700, QImage::Format_RGB32);
        base.fill(QColor("#2b3a55"));
        {
            QPainter p(&base);
            p.setPen(QColor(255, 255, 255, 60));
            for (int x = 0; x < base.width(); x += 40) p.drawLine(x, 0, x, base.height());
            for (int y = 0; y < base.height(); y += 40) p.drawLine(0, y, base.width(), y);
        }
        auto* ov = new Overlay(base, QRect(0, 0, 1000, 700), 1.0);
        ov->show();
        ov->demoSimPress(QPoint(200, 150));
        ov->demoSimMove(QPoint(420, 320));
        ov->demoSimMove(QPoint(650, 480));
        QImage during = ov->grab().toImage();
        during.save(outdir + "/select_during_drag.png");
        ov->demoSimRelease(QPoint(650, 480));
        QImage after = ov->grab().toImage();
        after.save(outdir + "/select_after_release.png");
        ov->deleteLater();

        // 取样对比：选区内 vs 选区外的亮度（验证暗色遮罩是否生效）
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
            ts << "during=" << during.width() << "x" << during.height() << "\n";
            ts << "after=" << after.width() << "x" << after.height() << "\n";
            ts << "insideGray=" << inside << " outsideGray=" << outside
               << " dimmed=" << ((outside < inside * 0.8) ? "true" : "false") << "\n";
            rf.close();
        }
        return 0;
    }

    // 标注自检：模拟鼠标手势，逐工具渲染，验证箭头/画笔/马赛克
    int anIdx = args.indexOf("--annot-selftest");
    if (anIdx >= 0) {
        QString outdir = (anIdx + 1 < args.size()) ? args[anIdx + 1] : ".";
        QDir().mkpath(outdir);
        QImage base(1400, 900, QImage::Format_RGB32);
        base.fill(Qt::white);
        {
            QPainter p(&base);
            p.setPen(QColor(230, 230, 230));
            for (int x = 0; x < base.width(); x += 50) p.drawLine(x, 0, x, base.height());
            for (int y = 0; y < base.height(); y += 50) p.drawLine(0, y, base.width(), y);
        }

        auto* ov = new Overlay(base, QRect(0, 0, 1400, 900), 1.0);
        ov->demoSelect(QRect(100, 60, 1200, 760));

        struct Case { Tool t; const char* name; QVector<QPoint> pts; };
        QVector<Case> cases;
        cases.append({Tool::Arrow, "arrow", {QPoint(320, 300), QPoint(700, 300), QPoint(700, 300), QPoint(700, 430)}});
        cases.append({Tool::Line, "line", {QPoint(900, 200), QPoint(1100, 380)}});
        {
            QVector<QPoint> pen;
            for (int i = 0; i < 30; ++i) pen.append(QPoint(300 + i * 18, 600 + int(qSin(i * 0.4) * 45)));
            cases.append({Tool::Pen, "pen", pen});
        }
        {
            QVector<QPoint> mos;
            for (int i = 0; i < 18; ++i) mos.append(QPoint(900 + i * 14, 560 + i * 6));
            cases.append({Tool::Mosaic, "mosaic", mos});
        }

        QStringList log;
        for (const Case& c : cases) {
            ov->demoSetTool(c.t);
            ov->demoSimPress(c.pts.first());
            for (int i = 1; i < c.pts.size(); ++i) ov->demoSimMove(c.pts[i]);
            ov->demoSimRelease(c.pts.last());

            QImage img = ov->demoFinal();
            img.save(QString("%1/annot_%2.png").arg(outdir, QString::fromLatin1(c.name)));
            QString detail;
            if (ov->demoAnnotCount() > 0) {
                Annotation a = ov->demoAnnot(ov->demoAnnotCount() - 1);
                detail = QString("type=%1 pts=%2").arg(int(a.type)).arg(a.pts.size());
            }
            log << QString("%1: annots=%2 %3").arg(QString::fromLatin1(c.name))
                       .arg(ov->demoAnnotCount()).arg(detail);
        }
        ov->deleteLater();

        QFile rf(outdir + "/annot_report.txt");
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts.setEncoding(QStringConverter::Utf8);
            for (const QString& l : log) ts << l << "\n";
            rf.close();
        }
        return 0;
    }

    // 录制方向自检：录 1 秒 -> 用 MF 解码首帧 -> 与原始抓屏比对（正向 / 上下翻转哪个更像）
    int oriIdx = args.indexOf("--record-orientation-selftest");
    if (oriIdx >= 0) {
        QString outMp4 = (oriIdx + 1 < args.size()) ? args[oriIdx + 1] : "ori.mp4";
        QString report = (oriIdx + 2 < args.size()) ? args[oriIdx + 2] : (outMp4 + ".txt");
        const QRect region(0, 0, 640, 360);

        QImage expected = capture::captureRect(region);
        Mp4Recorder rec;
        if (!rec.open(outMp4, region.width(), region.height(), 15, 8000, false)) {
            QFile rf(report);
            if (rf.open(QIODevice::WriteOnly)) rf.write(QString("open failed: %1\n").arg(rec.lastError()).toUtf8());
            return 16;
        }
        for (int i = 0; i < 12; ++i) {
            QImage f = capture::captureRect(region);
            if (!f.isNull()) rec.writeFrame(f);
            QThread::msleep(66);
        }
        rec.close();

        // 解码首帧
        MFStartup(MF_VERSION, MFSTARTUP_NOSOCKET);
        QImage decoded;
        qint64 hrOpen = 0, hrSetVal = 0, hrDecode = 0;
        UINT32 tw = 0, th = 0;
        {
            IMFSourceReader* reader = nullptr;
            IMFAttributes* attrs = nullptr;
            MFCreateAttributes(&attrs, 1);
            if (attrs) attrs->SetUINT32(MF_SOURCE_READER_ENABLE_VIDEO_PROCESSING, TRUE);
            HRESULT hr = MFCreateSourceReaderFromURL(reinterpret_cast<LPCWSTR>(outMp4.utf16()),
                                                     attrs, &reader);
            if (attrs) attrs->Release();
            qint64 hrOpen = hr;
            if (SUCCEEDED(hr) && reader) {
                IMFMediaType* outType = nullptr;
                MFCreateMediaType(&outType);
                outType->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Video);
                outType->SetGUID(MF_MT_SUBTYPE, MFVideoFormat_RGB32);
                HRESULT hrSet = reader->SetCurrentMediaType(0, nullptr, outType);
                outType->Release();
                qint64 hrSetVal = hrSet;

                IMFMediaType* cur = nullptr;
                if (SUCCEEDED(reader->GetCurrentMediaType(0, &cur)) && cur) {
                    MFGetAttributeSize(cur, MF_MT_FRAME_SIZE, &tw, &th);
                    cur->Release();
                }
                DWORD streamIndex = 0, flags = 0;
                LONGLONG ts = 0;
                IMFSample* sample = nullptr;
                qint64 lastHr = 0;
                for (int k = 0; k < 60 && !sample; ++k) {
                    HRESULT rs = reader->ReadSample(0, 0, &streamIndex, &flags, &ts, &sample);
                    lastHr = rs;
                    if (FAILED(rs)) break;
                    if (flags & MF_SOURCE_READERF_ENDOFSTREAM) break;
                    if (sample) break;
                }
                hrDecode = lastHr;
                if (sample) {
                    IMFMediaBuffer* buf = nullptr;
                    if (SUCCEEDED(sample->ConvertToContiguousBuffer(&buf)) && buf) {
                        BYTE* data = nullptr; DWORD len = 0;
                        if (SUCCEEDED(buf->Lock(&data, nullptr, &len)) && tw && th) {
                            decoded = QImage(int(tw), int(th), QImage::Format_RGB32);
                            const int stride = int(tw) * 4;
                            for (UINT32 y = 0; y < th; ++y)
                                memcpy(decoded.scanLine(int(y)), data + size_t(y) * stride, size_t(stride));
                            buf->Unlock();
                        }
                        buf->Release();
                    }
                    sample->Release();
                }
                reader->Release();
            }
        }
        MFShutdown();

        auto meanDiff = [](const QImage& a, const QImage& b) -> double {
            if (a.isNull() || b.isNull() || a.size() != b.size()) return 9999.0;
            long long s = 0, n = 0;
            for (int y = 0; y < a.height(); y += 4) {
                const QRgb* la = reinterpret_cast<const QRgb*>(a.constScanLine(y));
                const QRgb* lb = reinterpret_cast<const QRgb*>(b.constScanLine(y));
                for (int x = 0; x < a.width(); x += 4) {
                    s += qAbs(qGray(la[x]) - qGray(lb[x]));
                    n++;
                }
            }
            return n ? double(s) / n : 9999.0;
        };

        QImage flipped = decoded.mirrored(false, true);
        double dNorm = meanDiff(decoded, expected);
        double dFlip = meanDiff(flipped, expected);
        bool upright = dNorm < dFlip;

        QFile rf(report);
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts.setEncoding(QStringConverter::Utf8);
            ts << "fileSize=" << QFileInfo(outMp4).size() << "\n";
            ts << "hrOpen=" << hrOpen << " hrSetType=" << hrSetVal << " hrRead=" << hrDecode
               << " size=" << tw << "x" << th << "\n";
            ts << "decoded=" << decoded.width() << "x" << decoded.height() << "\n";
            ts << "diffNormal=" << dNorm << " diffFlipped=" << dFlip << "\n";
            ts << "upright=" << (upright ? "true" : "false") << "\n";
            rf.close();
        }
        if (!decoded.isNull()) decoded.save(outMp4 + ".frame.png");
        return upright ? 0 : 17;
    }

    // 译图自检：合成带文字的图 -> OCR -> 逐行翻译(mock) -> 渲染回原图
    int tiIdx = args.indexOf("--translate-image-selftest");
    if (tiIdx >= 0) {
        QString outdir = (tiIdx + 1 < args.size()) ? args[tiIdx + 1] : ".";
        QString base = (tiIdx + 2 < args.size()) ? args[tiIdx + 2] : "http://127.0.0.1:8899/v1";
        QDir().mkpath(outdir);

        QImage img(760, 260, QImage::Format_RGB32);
        img.fill(Qt::white);
        {
            QPainter p(&img);
            p.setPen(Qt::black);
            QFont f(QStringLiteral("Microsoft YaHei"));
            f.setPixelSize(34);
            p.setFont(f);
            p.drawText(40, 70, QStringLiteral("Open file and save as"));
            p.drawText(40, 140, QStringLiteral("Settings panel"));
            p.drawText(40, 210, QStringLiteral("Exit application"));
        }
        img.save(outdir + "/tr_input.png");

        QString err;
        // 本地模型已移除：这里用合成行验证“译文回填”渲染链路
        QVector<OcrLine> lines;
        {
            OcrLine a; a.text = QStringLiteral("Open file and save as"); a.score = 0.99f;
            a.box = QRect(47, 44, 420, 36); lines.append(a);
            OcrLine b; b.text = QStringLiteral("Settings panel"); b.score = 0.98f;
            b.box = QRect(46, 112, 300, 36); lines.append(b);
            OcrLine c; c.text = QStringLiteral("Exit application"); c.score = 0.97f;
            c.box = QRect(46, 183, 300, 36); lines.append(c);
        }
        bool ocrOk = !lines.isEmpty();

        ProviderPreset p;
        p.id = "mock";
        p.baseUrl = base + "/ok";
        p.model = "deepseek-flash";
        TranslateClient client;
        QStringList translated;
        int okCount = 0;
        for (const auto& l : lines) {
            auto r = client.translateLine(l.text, QStringLiteral("简体中文"), p, "sk-test",
                                          QStringLiteral("TackShot=TackShot"));
            translated << (r.ok ? r.text : QStringLiteral("[失败]"));
            if (r.ok) okCount++;
        }
        QImage composed = Overlay::renderTranslated(img, lines, translated);
        bool saved = composed.save(outdir + "/tr_result.png");

        QFile rf(outdir + "/translate_image_report.txt");
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts.setEncoding(QStringConverter::Utf8);
            ts << "ocrInit=" << (ocrOk ? "true" : "false") << " lines=" << lines.size()
               << " translated=" << okCount << " saved=" << (saved ? "true" : "false") << "\n";
            for (int i = 0; i < lines.size(); ++i)
                ts << "  [" << lines[i].box.x() << "," << lines[i].box.y() << "] "
                   << lines[i].text << "  ->  " << (i < translated.size() ? translated[i] : QString()) << "\n";
            rf.close();
        }
        bool pass = ocrOk && lines.size() >= 2 && okCount == lines.size() && saved;
        return pass ? 0 : 15;
    }

    // 翻译自检：正常 / 401 / 429 重试 / 分块 / 缓存 / 术语表 / 降级
    int trIdx = args.indexOf("--translate-selftest");
    if (trIdx >= 0) {
        QString base = (trIdx + 1 < args.size()) ? args[trIdx + 1] : "http://127.0.0.1:8899/v1";
        QString out = (trIdx + 2 < args.size()) ? args[trIdx + 2] : base + "_report.txt";

        auto mockRequests = [&]() -> int {
            QNetworkAccessManager mgr;
            QNetworkRequest req{QUrl("http://127.0.0.1:8899/stats")};
            req.setTransferTimeout(5000);
            QNetworkReply* rp = mgr.get(req);
            QEventLoop loop;
            QObject::connect(rp, &QNetworkReply::finished, &loop, &QEventLoop::quit);
            loop.exec();
            QByteArray body = rp->readAll();
            rp->deleteLater();
            auto doc = QJsonDocument::fromJson(body);
            return doc.object()["requests"].toInt();
        };

        ProviderPreset p;
        p.id = "mock";
        p.model = "deepseek-flash";
        TranslateClient client;
        QStringList log;
        bool allPass = true;

        // 1) 正常
        p.baseUrl = base + "/ok";
        TranslateCache::get().clear();
        auto r1 = client.translateLong(QStringLiteral("Hello, world"), QStringLiteral("简体中文"),
                                       p, "sk-test", QString(), 1500, true);
        bool p1 = r1.ok && !r1.text.isEmpty() && r1.chunkCount == 1;
        log << QString("normal: ok=%1 chunks=%2 text=%3 pass=%4")
                   .arg(r1.ok).arg(r1.chunkCount).arg(r1.text.left(16)).arg(p1);
        allPass &= p1;

        // 2) 401 不重试
        p.baseUrl = base + "/bad";
        auto r2 = client.translateLong(QStringLiteral("hello"), QStringLiteral("简体中文"),
                                       p, "sk-bad", QString(), 1500, false);
        bool p2 = !r2.ok && r2.chunkFailed == 1;
        log << QString("auth401: ok=%1 chunkFailed=%2 err=%3 pass=%4")
                   .arg(r2.ok).arg(r2.chunkFailed).arg(r2.error.left(24)).arg(p2);
        allPass &= p2;

        // 3) 429 重试到成功
        p.baseUrl = base + "/flaky";
        auto r3 = client.translateLong(QStringLiteral("hello"), QStringLiteral("简体中文"),
                                       p, "sk-test", QString(), 1500, false);
        bool p3 = r3.ok;
        log << QString("retry429: ok=%1 text=%2 pass=%3")
                   .arg(r3.ok).arg(r3.text.left(16)).arg(p3);
        allPass &= p3;

        // 4) 分块：40 段 x 40 字，chunk=500 -> 至少 3 块
        p.baseUrl = base + "/ok";
        QStringList paras;
        for (int i = 0; i < 40; ++i)
            paras << QString("第%1段：这是一段用于测试分块的中文文本，长度大约四十个字符左右。").arg(i + 1);
        QString longText = paras.join("\n");
        int before = mockRequests();
        auto r4 = client.translateLong(longText, QStringLiteral("简体中文"), p, "sk-test",
                                       QString(), 500, false);
        int after = mockRequests();
        bool p4 = r4.ok && r4.chunkCount >= 3 && (after - before) == r4.chunkCount;
        log << QString("chunk: ok=%1 chunks=%2 requests=%3 pass=%4")
                   .arg(r4.ok).arg(r4.chunkCount).arg(after - before).arg(p4);
        allPass &= p4;

        // 5) 缓存：同一段再翻一次，不应产生新请求
        int before2 = mockRequests();
        auto r5 = client.translateLong(QStringLiteral("Hello, world"), QStringLiteral("简体中文"),
                                       p, "sk-test", QString(), 1500, true);
        int after2 = mockRequests();
        bool p5 = r5.ok && r5.fromCache && (after2 == before2) && r5.text == r1.text;
        log << QString("cache: ok=%1 fromCache=%2 newRequests=%3 pass=%4")
                   .arg(r5.ok).arg(r5.fromCache).arg(after2 - before2).arg(p5);
        allPass &= p5;

        // 6) 术语表：mock 在 system 里看到“术语表”会回 GLOSSARY_OK 前缀
        auto r6 = client.translateLong(QStringLiteral("TackShot is great"), QStringLiteral("简体中文"),
                                       p, "sk-test", QStringLiteral("TackShot=塔克肖特"), 1500, false);
        bool p6 = r6.ok && r6.text.contains("GLOSSARY_OK");
        log << QString("glossary: ok=%1 marker=%2 pass=%3")
                   .arg(r6.ok).arg(r6.text.left(14)).arg(p6);
        allPass &= p6;

        // 7) 降级：主引擎 401 -> 备用引擎成功
        ProviderPreset bad = p; bad.id = "primary"; bad.baseUrl = base + "/bad";
        ProviderPreset good = p; good.id = "backup"; good.baseUrl = base + "/ok";
        auto ra = client.translateLong(QStringLiteral("hello"), QStringLiteral("简体中文"),
                                       bad, "sk-bad", QString(), 1500, false);
        auto rb = client.translateLong(QStringLiteral("hello"), QStringLiteral("简体中文"),
                                       good, "sk-ok", QString(), 1500, false);
        bool p7 = !ra.ok && rb.ok;
        log << QString("fallback: primaryOk=%1 backupOk=%2 pass=%3")
                   .arg(ra.ok).arg(rb.ok).arg(p7);
        allPass &= p7;

        log << QString("ALL_PASS=%1").arg(allPass ? "true" : "false");
        QFile rf(out);
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts.setEncoding(QStringConverter::Utf8);
            for (const auto& l : log) ts << l << "\n";
            rf.close();
        }
        return allPass ? 0 : 13;
    }

    // DPI 自检：逐屏校验 物理=逻辑×dpr，以及覆盖层映射比例
    int dpiIdx = args.indexOf("--dpi-selftest");
    if (dpiIdx >= 0) {
        QString out = (dpiIdx + 1 < args.size()) ? args[dpiIdx + 1] : "dpi.txt";
        QRect virt;
        QImage shot = capture::captureVirtualDesktop(&virt, nullptr);
        const auto screens = QGuiApplication::screens();
        bool allPass = true;

        QFile rf(out);
        rf.open(QIODevice::WriteOnly);
        QTextStream ts(&rf);
        ts.setEncoding(QStringConverter::Utf8);
        ts << "screens=" << screens.size() << " capture=" << shot.width() << "x" << shot.height()
           << " virt=" << virt.x() << "," << virt.y() << "\n";

        for (QScreen* sc : screens) {
            const qreal dpr = sc->devicePixelRatio();
            QRect phys = screenPhysicalRect(sc);
            QRect inShot = phys.translated(-virt.topLeft());
            bool inside = shot.rect().contains(inShot);
            QImage part = inside && !shot.isNull() ? shot.copy(inShot) : QImage();

            ts << "screen " << sc->name() << "\n";
            ts << "  logical=" << sc->geometry().x() << "," << sc->geometry().y() << " "
               << sc->geometry().width() << "x" << sc->geometry().height() << " dpr=" << dpr << "\n";
            ts << "  physical=" << phys.x() << "," << phys.y() << " " << phys.width() << "x" << phys.height()
               << " insideCapture=" << (inside ? "true" : "false") << "\n";

            if (!inside || part.isNull()) { ts << "  pass=false (超出抓屏范围)\n"; allPass = false; continue; }

            auto* ov = new Overlay(part, phys, dpr);
            QPoint wpt(100, 60);
            QPoint ipt = ov->demoMapToImage(wpt);
            double ratio = wpt.x() ? double(ipt.x()) / wpt.x() : 0;
            double errW = qAbs(ov->width() * dpr - part.width());
            bool pass = (qAbs(ratio - dpr) < 0.02) && (errW <= 2.0);
            ts << "  overlayLogical=" << ov->width() << "x" << ov->height()
               << " scale=" << ov->demoScale()
               << " mapRatio=" << ratio << " widthError=" << errW
               << " pass=" << (pass ? "true" : "false") << "\n";
            if (!pass) allPass = false;
            ov->deleteLater();
        }
        ts << "ALL_PASS=" << (allPass ? "true" : "false") << "\n";
        rf.close();
        return allPass ? 0 : 12;
    }

    // 音频自检：播放 1kHz 音调    // 音频自检：播放 1kHz 音调 -> 系统回环采集 -> 直接写 MP4（含 AAC）
    int auIdx = args.indexOf("--audio-selftest");
    if (auIdx >= 0) {
        QString out = (auIdx + 1 < args.size()) ? args[auIdx + 1] : "audio.mp4";
        double seconds = (auIdx + 2 < args.size()) ? args[auIdx + 2].toDouble() : 3.0;

        // 生成 1kHz 正弦 WAV（16bit/48k/立体声）
        QString wavPath = QDir::tempPath() + "/tackshot_tone.wav";
        {
            const int rate = 48000, ch = 2, secs = 5;
            QByteArray pcm;
            pcm.resize(rate * ch * 2 * secs);
            qint16* p = reinterpret_cast<qint16*>(pcm.data());
            for (int i = 0; i < rate * secs; ++i) {
                qint16 v = qint16(12000 * qSin(2.0 * M_PI * 1000.0 * i / rate));
                p[i * 2] = v; p[i * 2 + 1] = v;
            }
            QFile wf(wavPath);
            if (wf.open(QIODevice::WriteOnly)) {
                auto w32 = [&](quint32 v) { wf.write(reinterpret_cast<const char*>(&v), 4); };
                auto w16 = [&](quint16 v) { wf.write(reinterpret_cast<const char*>(&v), 2); };
                wf.write("RIFF", 4); w32(36 + pcm.size()); wf.write("WAVE", 4);
                wf.write("fmt ", 4); w32(16); w16(1); w16(ch); w32(rate); w32(rate * ch * 2); w16(ch * 2); w16(16);
                wf.write("data", 4); w32(pcm.size()); wf.write(pcm);
                wf.close();
            }
        }
        PlaySoundW(reinterpret_cast<LPCWSTR>(wavPath.utf16()), nullptr, SND_FILENAME | SND_ASYNC | SND_LOOP);

        Mp4Recorder rec;
        QString err;
        bool okOpen = rec.open(out, 640, 360, 15, 4000, true, 48000, 2);

        AudioCapture mic;
        bool micOk = mic.start(AudioCapture::SystemLoopback);

        int frames = 0;
        qint64 audioBytes = 0;
        double sumSq = 0.0;
        long long nSamples = 0;
        int peak = 0;
        QElapsedTimer t; t.start();
        while (t.elapsed() < seconds * 1000 && okOpen && micOk) {
            QImage part = capture::captureRect(QRect(0, 0, 640, 360));
            if (!part.isNull()) { rec.writeFrame(part); frames++; }
            QByteArray pcm = mic.read();
            if (!pcm.isEmpty()) {
                rec.writeAudio(pcm);
                audioBytes += pcm.size();
                const qint16* s16 = reinterpret_cast<const qint16*>(pcm.constData());
                int n = pcm.size() / 2;
                for (int i = 0; i < n; ++i) {
                    int v = s16[i];
                    peak = qMax(peak, qAbs(v));
                    sumSq += double(v) * v;
                    nSamples++;
                }
            }
            QThread::msleep(66);
        }
        bool ok = okOpen ? rec.close() : false;
        PlaySoundW(nullptr, nullptr, 0);
        mic.stop();

        QFile rf(out + ".txt");
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts << "open=" << (okOpen ? "true" : "false") << " capture=" << (micOk ? "true" : "false") << "\n";
            if (!micOk) ts << "captureError=" << mic.lastError() << "\n";
            if (!okOpen) ts << "openError=" << rec.lastError() << "\n";
            ts << "frames=" << frames << " audioBytes=" << audioBytes << "\n";
            ts << "rms=" << (nSamples ? qSqrt(sumSq / nSamples) : 0.0)
               << " peak=" << peak << "\n";
            ts << "bytes=" << QFileInfo(out).size() << "\n";
            rf.close();
        }
        QFile::remove(wavPath);
        return ok || micOk ? 0 : 11;
    }

    // MP4 录制自检：录制屏幕左上角 640x360，固定秒数
    int recIdx = args.indexOf("--record-selftest");
    if (recIdx >= 0) {
        QString out = (recIdx + 1 < args.size()) ? args[recIdx + 1] : "record.mp4";
        double seconds = (recIdx + 2 < args.size()) ? args[recIdx + 2].toDouble() : 3.0;
        QRect region(0, 0, 640, 360);
        Mp4Recorder rec;
        QString err;
        if (!rec.open(out, region.width(), region.height(), 15, 6000)) {
            QFile rf(out + ".txt");
            if (rf.open(QIODevice::WriteOnly))
                rf.write(QString("open failed: %1\n").arg(rec.lastError()).toUtf8());
            return 9;
        }
        int frames = 0;
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
        bool ok = rec.close();
        QFile rf(out + ".txt");
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts << "ok=" << (ok ? "true" : "false") << " frames=" << frames
               << " avgCapMs=" << (frames ? double(capMs)/frames : -1)
               << " avgEncMs=" << (frames ? double(encMs)/frames : -1)
               << " bytes=" << QFileInfo(out).size() << "\n";
            rf.close();
        }
        return ok ? 0 : 10;
    }

    // 撤销/重做自检
    int unIdx = args.indexOf("--undo-selftest");
    if (unIdx >= 0) {
        QString out = (unIdx + 1 < args.size()) ? args[unIdx + 1] : "undo.txt";
        QImage dummy(200, 200, QImage::Format_RGB32);
        dummy.fill(Qt::white);
        auto* ov = new Overlay(dummy, QRect(0, 0, 200, 200), 1.0);
        QVector<int> seq = ov->demoUndoTest();
        ov->deleteLater();
        QFile rf(out);
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts << "counts=";
            for (int i = 0; i < seq.size(); ++i) ts << (i ? "," : "") << seq[i];
            ts << "\n";
            rf.close();
        }
        return 0;
    }

    // 长截图拼接自检：合成一张长图，切成重叠帧，再拼回去比对
    int lsIdx = args.indexOf("--longshot-selftest");
    if (lsIdx >= 0) {
        QString outdir = (lsIdx + 1 < args.size()) ? args[lsIdx + 1] : ".";
        QDir().mkpath(outdir);
        const int W = 600, H = 1800, FH = 600, STEP = 500;
        QImage full(W, H, QImage::Format_RGB32);
        {
            QPainter p(&full);
            for (int y = 0; y < H; ++y) {
                QColor c = QColor::fromHsv((y * 7) % 360, 60, 235 - (y % 40));
                p.fillRect(0, y, W, 1, c);
            }
            QFont f(QStringLiteral("Microsoft YaHei"));
            f.setPixelSize(26);
            p.setFont(f);
            p.setPen(Qt::black);
            for (int i = 0; i < 18; ++i)
                p.drawText(40, 100 + i * 96, QString("第 %1 行  long-shot stitching test  %2").arg(i + 1).arg(i * 37));
        }
        full.save(outdir + "/longshot_source.png");

        QImage canvas;
        int matched = 0, frames = 0;
        for (int y = 0; y + FH <= H; y += STEP) {
            QImage frame = full.copy(0, y, W, FH);
            bool m = false;
            canvas = longshot::appendFrame(canvas, frame, &m);
            frames++;
            if (m) matched++;
        }
        canvas.save(outdir + "/longshot_result.png");

        // ---- 横向：合成一张宽图，按列切帧，用 appendAuto 拼接 ----
        const int HW = 1800, HH = 600, FW = 600, HSTEP = 500;
        QImage wide(HW, HH, QImage::Format_RGB32);
        {
            QPainter p(&wide);
            for (int x = 0; x < HW; ++x) {
                QColor c = QColor::fromHsv((x * 5) % 360, 60, 235 - (x % 40));
                p.fillRect(x, 0, 1, HH, c);
            }
            QFont f(QStringLiteral("Microsoft YaHei"));
            f.setPixelSize(26);
            p.setFont(f);
            p.setPen(Qt::black);
            for (int i = 0; i < 18; ++i)
                p.drawText(60 + i * 96, 120, QString("列 %1").arg(i + 1));
        }
        wide.save(outdir + "/longshot_wide_source.png");

        QImage hcanvas;
        int hmatched = 0, hframes = 0, hdir = -1;
        for (int x = 0; x + FW <= HW; x += HSTEP) {
            QImage frame = wide.copy(x, 0, FW, HH);
            bool m = false;
            int d = 0;
            hcanvas = longshot::appendAuto(hcanvas, frame, &d, &m);
            hframes++;
            if (m) { hmatched++; hdir = d; }
        }
        hcanvas.save(outdir + "/longshot_wide_result.png");

        int hcmpW = qMin(hcanvas.width(), wide.width()), hcmpH = HH;
        long long hdiff = 0, hn = 0;
        for (int y = 0; y < hcmpH; y += 3) {
            const QRgb* a = reinterpret_cast<const QRgb*>(hcanvas.constScanLine(y));
            const QRgb* b = reinterpret_cast<const QRgb*>(wide.constScanLine(y));
            for (int x = 0; x < hcmpW; x += 3) { hdiff += qAbs(qGray(a[x]) - qGray(b[x])); hn++; }
        }
        QFile hrf(outdir + "/longshot_wide_report.txt");
        if (hrf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&hrf);
            ts.setEncoding(QStringConverter::Utf8);
            ts << "frames=" << hframes << " matched=" << hmatched << " dir=" << hdir << "\n";
            ts << "canvas=" << hcanvas.width() << "x" << hcanvas.height()
               << " source=" << wide.width() << "x" << wide.height() << "\n";
            ts << "meanAbsDiff=" << (hn ? double(hdiff) / hn : -1) << "\n";
            hrf.close();
        }

        // 与源图比对（取交集高度）
        int cmpW = W, cmpH = qMin(canvas.height(), full.height());
        long long diff = 0; long long n = 0;
        for (int y = 0; y < cmpH; y += 3) {
            const QRgb* a = reinterpret_cast<const QRgb*>(canvas.constScanLine(y));
            const QRgb* b = reinterpret_cast<const QRgb*>(full.constScanLine(y));
            for (int x = 0; x < cmpW; x += 3) {
                diff += qAbs(qGray(a[x]) - qGray(b[x]));
                n++;
            }
        }
        QFile rf(outdir + "/longshot_report.txt");
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts.setEncoding(QStringConverter::Utf8);
            ts << "frames=" << frames << " matched=" << matched << "\n";
            ts << "canvas=" << canvas.width() << "x" << canvas.height()
               << " source=" << full.width() << "x" << full.height() << "\n";
            ts << "meanAbsDiff=" << (n ? double(diff) / n : -1) << "\n";
            rf.close();
        }
        return 0;
    }

    // GIF 编码自检：合成动画 -> 编码 -> 统计
    int gifIdx = args.indexOf("--gif-selftest");
    if (gifIdx >= 0) {
        QString out = (gifIdx + 1 < args.size()) ? args[gifIdx + 1] : "selftest.gif";
        GifEncoder enc;
        if (!enc.open(out, 320, 180, 8)) return 7;
        for (int i = 0; i < 24; ++i) {
            QImage f(320, 180, QImage::Format_RGB32);
            f.fill(QColor::fromHsv((i * 15) % 360, 40, 220));
            QPainter p(&f);
            p.setRenderHint(QPainter::Antialiasing);
            p.setBrush(QColor("#1f4fd0"));
            p.setPen(Qt::NoPen);
            p.drawEllipse(QPoint(40 + i * 10, 90), 26, 26);
            p.setPen(Qt::black);
            QFont fnt(QStringLiteral("Microsoft YaHei"));
            fnt.setPixelSize(22);
            p.setFont(fnt);
            p.drawText(20, 30, QString("frame %1").arg(i));
            enc.addFrame(f);
        }
        bool ok = enc.close();
        int bytes = QFileInfo(out).size();
        QFile rf(out + ".txt");
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts.setEncoding(QStringConverter::Utf8);
            ts << "ok=" << (ok ? "true" : "false") << " frames=" << enc.frameCount()
               << " bytes=" << bytes << "\n";
            rf.close();
        }
        return ok ? 0 : 8;
    }

    // OCR 自检：合成一张带文字的图，跑本地识别并落盘结果

    // 自检模式：抓屏并落盘，用于自动化验证
    int stIdx = args.indexOf("--selftest");
    if (stIdx >= 0) {
        QString out = (stIdx + 1 < args.size()) ? args[stIdx + 1] : "selftest.png";
        QRect rect;
        QString err;
        QImage shot = capture::captureVirtualDesktop(&rect, &err);
        QString reportPath = out + ".txt";
        if (shot.isNull()) {
            QFile rf(reportPath);
            if (rf.open(QIODevice::WriteOnly))
                rf.write(QString("capture FAILED: %1\n").arg(err).toUtf8());
            return 2;
        }
        bool ok = shot.save(out);
        {
            QFile rf(reportPath);
            if (rf.open(QIODevice::WriteOnly)) {
                QString info;
                info += QString("version=%1\n").arg(APP_VERSION);
                info += QString("qt=%1\n").arg(qVersion());
                info += QString("capture=%1x%2\n").arg(shot.width()).arg(shot.height());
                info += QString("virtualRect=%1,%2 %3x%4\n").arg(rect.x()).arg(rect.y()).arg(rect.width()).arg(rect.height());
                info += QString("dxgiAvailable=%1\n").arg(capture::dxgiAvailable() ? "true" : "false");
                info += QString("screens=%1\n").arg(QGuiApplication::screens().size());
                for (QScreen* s : QGuiApplication::screens())
                    info += QString("  screen %1 geom=%2,%3 %4x%5 dpr=%6\n")
                        .arg(s->name()).arg(s->geometry().x()).arg(s->geometry().y())
                        .arg(s->geometry().width()).arg(s->geometry().height())
                        .arg(s->devicePixelRatio());
                info += QString("saved=%1\n").arg(ok ? "true" : "false");
                rf.write(info.toUtf8());
            }
        }
        QImage probe = shot;
        QPainter p(&probe);
        p.setPen(QPen(QColor("#ff0000"), 6));
        p.drawRect(100, 100, 400, 300);
        p.fillRect(QRect(60, 60, 40, 40), QColor("#00ff00"));
        p.end();
        bool ok2 = probe.save(out + ".probe.png");
        printf("probe saved=%d\n", int(ok2));
        return ok ? 0 : 3;
    }

    // 界面渲染自检：用合成底图跑一遍覆盖层 + 标注，落盘快照（不接触真实桌面）
    int odIdx = args.indexOf("--overlay-demo");
    if (odIdx >= 0) {
        QString out = (odIdx + 1 < args.size()) ? args[odIdx + 1] : "overlay.png";
        QSize sz(1600, 1000);
        QImage base(sz, QImage::Format_ARGB32);
        {
            QPainter p(&base);
            QLinearGradient g(0, 0, sz.width(), sz.height());
            g.setColorAt(0, QColor("#1d2433"));
            g.setColorAt(1, QColor("#3a2b52"));
            p.fillRect(base.rect(), g);
            p.setPen(QColor(255, 255, 255, 28));
            for (int x = 0; x < sz.width(); x += 40) p.drawLine(x, 0, x, sz.height());
            for (int y = 0; y < sz.height(); y += 40) p.drawLine(0, y, sz.width(), y);
            p.setPen(QColor("#ffffff"));
            QFont f = p.font();
            f.setPixelSize(34);
            f.setBold(true);
            p.setFont(f);
            p.drawText(QRect(60, 40, 1200, 60), Qt::AlignLeft, QStringLiteral("TackShot — 合成底图（无需真实屏幕）"));
        }
        auto* ov = new Overlay(base, QRect(0, 0, sz.width(), sz.height()), 1.0);
        ov->demoSetup();
        ov->show();
        ov->raise();
        if (args.contains("--final")) {
            QImage finalImg = ov->demoFinal();
            bool ok = finalImg.save(out);
            QFile rf(out + ".txt");
            if (rf.open(QIODevice::WriteOnly))
                rf.write(QString("final=%1x%2\nsaved=%3\n").arg(finalImg.width()).arg(finalImg.height()).arg(ok ? "true" : "false").toUtf8());
            return ok ? 0 : 4;
        }
        QTimer::singleShot(700, [ov, out]() {
            QPixmap snap = ov->grab();
            bool ok = snap.save(out);
            QFile rf(out + ".txt");
            if (rf.open(QIODevice::WriteOnly))
                rf.write(QString("overlay=%1x%2\nsaved=%3\n").arg(snap.width()).arg(snap.height()).arg(ok ? "true" : "false").toUtf8());
            qApp->quit();
        });
        return app.exec();
    }

    Config::get().load();

    // 单实例
    QLocalSocket probeSock;
    probeSock.connectToServer("TackShotInstance");
    if (probeSock.waitForConnected(1500)) {
        probeSock.write("capture");
        probeSock.flush();
        probeSock.waitForBytesWritten(500);
        return 0;
    }
    static QLocalServer server;
    QLocalServer::removeServer("TackShotInstance");
    if (!server.listen("TackShotInstance"))
        qWarning() << "single-instance server unavailable (named pipe blocked?)";
    QObject::connect(&server, &QLocalServer::newConnection, [&]() {
        QLocalSocket* s = server.nextPendingConnection();
        if (s) {
            QObject::connect(s, &QLocalSocket::readyRead, [s]() {
                QString cmd = QString::fromUtf8(s->readAll());
                if (cmd.contains("capture")) doCapture();
                s->deleteLater();
            });
        }
    });

    QIcon icon = makeAppIcon();

    g_hotkey = new HotkeyManager(&app);
    QObject::connect(g_hotkey, &HotkeyManager::activated, []() { doCapture(); });

    g_tray = new QSystemTrayIcon(icon, &app);

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

    QKeySequence hotkeySeq(Qt::Key(Config::get().hotkeyVk), Qt::KeyboardModifiers(Config::get().hotkeyMods));
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
        actCapture->setShortcut(QKeySequence(Qt::Key(Config::get().hotkeyVk),
                                             Qt::KeyboardModifiers(Config::get().hotkeyMods)));
        actCapture->setShortcutVisibleInContextMenu(true);
        menu->update();
    });

    g_tray->setContextMenu(menu);
    g_tray->setToolTip(QStringLiteral("TackShot — 点击截图"));
    g_tray->show();
    QObject::connect(g_tray, &QSystemTrayIcon::activated, [](QSystemTrayIcon::ActivationReason r) {
        if (r == QSystemTrayIcon::Trigger) doCapture();
    });

    if (!g_hotkey->install(Config::get().hotkeyMods, Config::get().hotkeyVk))
        g_tray->showMessage(QStringLiteral("TackShot"),
            QStringLiteral("热键 %1 注册失败，可能被其他程序占用").arg(Config::get().hotkeyText()),
            QSystemTrayIcon::Warning, 5000);

    // 命令行 --capture：启动后立刻截图
    if (args.contains("--capture"))
        QTimer::singleShot(150, []() { doCapture(); });

    return app.exec();
}
