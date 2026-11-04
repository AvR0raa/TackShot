import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
if "--cloud-selftest" not in s:
    s = s.replace('#include "formula.h"', '#include "formula.h"\n#include "baidu.h"\n#include "simpletex.h"')
    anchor = "    // 在线视觉识别自检"
    code = r'''    // 云端识别自检：百度图片翻译 + SimpleTex 公式（对着 mock 跑）
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

'''
    if anchor in s:
        s = s.replace(anchor, code + anchor, 1)
        io.open(p, "w", encoding="utf-8").write(s)
print("cloud selftest added")
