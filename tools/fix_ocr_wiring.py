import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()

old = """    {
        QString key = secrets::load("vision_api_key_" + cfg.visionProvider);
        if (key.isEmpty()) key = secrets::load("translate_api_key_" + cfg.visionProvider);
        dlg.setOnlineAvailable(!key.isEmpty());
    }"""
new = """    {
        // 翻译/译图按钮是否可用，取决于“翻译 API Key”，与视觉模型 Key 无关
        bool anyTranslateKey = !secrets::load("translate_api_key").isEmpty();
        if (!anyTranslateKey) {
            for (const auto& p : TranslateClient::presets()) {
                if (!secrets::load("translate_api_key_" + p.id).isEmpty()) { anyTranslateKey = true; break; }
            }
        }
        dlg.setOnlineAvailable(anyTranslateKey);
    }"""
if old in s:
    s = s.replace(old, new, 1)

old2 = """        if (fr.init(QString(), &ferr)) {
            const QString latex = fr.recognize(img);
            if (!latex.isEmpty()) dlg.setLatex(latex);
        }
        unsetCursor();"""
new2 = """        if (fr.init(QString(), &ferr)) {
            const QString latex = fr.recognize(img);
            if (!latex.isEmpty()) {
                dlg.setLatex(latex);
                // setLatex 会自动切到 LaTeX 页；识别结果默认仍应停在「文字」页
                if (auto* tabs = dlg.findChild<QTabWidget*>()) tabs->setCurrentIndex(0);
            }
        }
        unsetCursor();"""
if old2 in s:
    s = s.replace(old2, new2, 1)

if "#include <QTabWidget>" not in s:
    s = s.replace("#include <QTextStream>", "#include <QTextStream>\n#include <QTabWidget>")
io.open(p, "w", encoding="utf-8").write(s)
print("fixed online-availability + default tab")
