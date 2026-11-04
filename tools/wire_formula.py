import io, os, shutil

# formula.cpp 补 include
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\formula.cpp"
s = io.open(p, encoding="utf-8").read()
if "#include <QRegularExpression>" not in s:
    s = s.replace("#include <QDir>", "#include <QDir>\n#include <QRegularExpression>")
io.open(p, "w", encoding="utf-8").write(s)

# main.cpp：--formula-selftest
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
if "--formula-selftest" not in s:
    s = s.replace('#include "vision.h"', '#include "vision.h"\n#include "formula.h"')
    anchor = "    // 在线视觉识别自检"
    code = r'''    // 本地公式模型自检：给一张公式图，输出 LaTeX
    int fmIdx = args.indexOf("--formula-selftest");
    if (fmIdx >= 0) {
        QString imgPath = (fmIdx + 1 < args.size()) ? args[fmIdx + 1] : "formula.png";
        QString outTxt = (fmIdx + 2 < args.size()) ? args[fmIdx + 2] : (imgPath + ".txt");
        QImage img(imgPath);
        QString err;
        FormulaRecognizer& fr = FormulaRecognizer::get();
        QString latex;
        QElapsedTimer t; t.start();
        if (fr.init(QString(), &err)) latex = fr.recognize(img);
        const qint64 ms = t.elapsed();

        QFile f(outTxt);
        if (f.open(QIODevice::WriteOnly)) {
            QTextStream ts(&f);
            ts.setEncoding(QStringConverter::Utf8);
            ts << "image=" << imgPath << " " << img.width() << "x" << img.height() << "\n";
            ts << "ready=" << (fr.ready() ? "true" : "false") << " err=" << err << "\n";
            ts << "ms=" << ms << "\n";
            ts << "latex=" << latex << "\n";
            f.close();
        }
        return latex.isEmpty() ? 22 : 0;
    }

'''
    if anchor in s:
        s = s.replace(anchor, code + anchor, 1)
    io.open(p, "w", encoding="utf-8").write(s)

# 拷贝模型到 dist
src = r"C:\Users\laiki\.dsh\workspace\tackshot\dl\models\pix2text-mfr-1.5"
dst = r"C:\Users\laiki\.dsh\workspace\tackshot\dist\TackShot\models\formula"
os.makedirs(dst, exist_ok=True)
total = 0
for name in ["encoder_model.onnx", "decoder_model.onnx", "tokenizer.json", "config.json",
             "generation_config.json", "preprocessor_config.json"]:
    sp = os.path.join(src, name)
    if os.path.exists(sp):
        shutil.copy2(sp, os.path.join(dst, name))
        total += os.path.getsize(sp)
print("models copied: %.1f MB" % (total / 1048576))
