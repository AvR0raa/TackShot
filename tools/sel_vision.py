import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()

if '#include "vision.h"' not in s:
    s = s.replace('#include "ocr.h"', '#include "ocr.h"\n#include "ocrdialog.h"\n#include "vision.h"')

anchor = "    // 纯抓屏诊断"
code = r'''    // 在线视觉识别自检：跑 mock 服务器的三个端点
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
    int odIdx = args.indexOf("--ocr-dialog-preview");
    if (odIdx >= 0) {
        QString outPng = (odIdx + 1 < args.size()) ? args[odIdx + 1] : "ocrdialog.png";
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

'''
if anchor in s:
    s = s.replace(anchor, code + anchor, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("selftests added")
else:
    print("MISS")
