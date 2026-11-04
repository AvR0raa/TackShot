import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
if '#include "formula.h"' not in s:
    s = s.replace('#include "vision.h"', '#include "vision.h"\n#include "formula.h"')

old = """    {
        QString key = secrets::load("vision_api_key_" + cfg.visionProvider);
        if (key.isEmpty()) key = secrets::load("translate_api_key_" + cfg.visionProvider);
        dlg.setOnlineAvailable(!key.isEmpty());
    }"""
new = """    {
        QString key = secrets::load("vision_api_key_" + cfg.visionProvider);
        if (key.isEmpty()) key = secrets::load("translate_api_key_" + cfg.visionProvider);
        dlg.setOnlineAvailable(!key.isEmpty());
    }

    // 本地公式识别：把整块选区送进 TrOCR，结果填进 LaTeX 页
    if (cfg.ocrFormula) {
        setCursor(Qt::WaitCursor);
        QCoreApplication::processEvents();
        FormulaRecognizer& fr = FormulaRecognizer::get();
        QString ferr;
        if (fr.init(QString(), &ferr)) {
            const QString latex = fr.recognize(img);
            if (!latex.isEmpty()) dlg.setLatex(latex);
        }
        unsetCursor();
    }"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("formula wired into onOcr")
else:
    print("MISS")
