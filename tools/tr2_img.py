import io

# overlay.h: 暴露 renderTranslated
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace('#include "annotate.h"', '#include "annotate.h"\n#include "ocr.h"')
s = s.replace("    QVector<int> demoUndoTest();",
"""    QVector<int> demoUndoTest();

    // 把译文渲染回原图（译图功能，自检也会用）
    static QImage renderTranslated(const QImage& base, const QVector<OcrLine>& lines,
                                   const QStringList& translated);""")
io.open(p, "w", encoding="utf-8").write(s)

# overlay.cpp: 静态函数改成类静态成员
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("""// 按选区尺寸把译文渲染回原图（图片翻译）
static QImage renderTranslation(const QImage& base, const QVector<OcrLine>& lines,
                                const QStringList& translated) {""",
"""// 按选区尺寸把译文渲染回原图（图片翻译）
QImage Overlay::renderTranslated(const QImage& base, const QVector<OcrLine>& lines,
                                 const QStringList& translated) {""")
s = s.replace("QImage composed = renderTranslation(img, lines, translated);",
              "QImage composed = renderTranslated(img, lines, translated);")
io.open(p, "w", encoding="utf-8").write(s)
print("renderTranslated exposed")

# main.cpp: 译图自检
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
anchor = "    // 翻译自检：正常 / 401"
code = '''    // 译图自检：合成带文字的图 -> OCR -> 逐行翻译(mock) -> 渲染回原图
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

        Ocr& ocr = Ocr::get();
        QString err;
        bool ocrOk = ocr.init(&err);
        QVector<OcrLine> lines = ocrOk ? ocr.recognize(img, &err) : QVector<OcrLine>();

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
               << " translated=" << okCount << " saved=" << (saved ? "true" : "false") << "\\n";
            for (int i = 0; i < lines.size(); ++i)
                ts << "  [" << lines[i].box.x() << "," << lines[i].box.y() << "] "
                   << lines[i].text << "  ->  " << (i < translated.size() ? translated[i] : QString()) << "\\n";
            rf.close();
        }
        bool pass = ocrOk && lines.size() >= 2 && okCount == lines.size() && saved;
        return pass ? 0 : 15;
    }

'''
if anchor in s:
    s = s.replace(anchor, code + anchor, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("image selftest added")
else:
    print("MISS")
