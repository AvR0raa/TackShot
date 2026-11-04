import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()

start = s.index("void Overlay::onOcr() {")
end = s.index("void Overlay::onLongShot() {")
new = r'''void Overlay::onOcr() {
    QImage img = selectionImage(false);
    if (img.isNull()) return;

    Config& cfg = Config::get();
    const QString backend = cfg.ocrBackend.isEmpty() ? QStringLiteral("local") : cfg.ocrBackend;

    QVector<OcrLine> lines;
    QString usedBackend;
    QString err;
    qint64 elapsed = 0;

    auto runLocal = [&]() -> bool {
        QElapsedTimer t; t.start();
        Ocr& ocr = Ocr::get();
        if (!ocr.init(&err)) return false;
        lines = ocr.recognize(img, &err);
        elapsed = t.elapsed();
        usedBackend = QStringLiteral("本地 OCR");
        return !lines.isEmpty();
    };

    auto visionPreset = [&]() {
        ProviderPreset vp = TranslateClient::presetById(cfg.visionProvider);
        if (!cfg.visionBaseUrl.isEmpty()) vp.baseUrl = cfg.visionBaseUrl;
        if (!cfg.visionModel.isEmpty()) vp.model = cfg.visionModel;
        return vp;
    };

    auto runOnline = [&]() -> bool {
        if (!cfg.ocrPrivacyAccepted) {
            const auto ans = QMessageBox::question(
                this, QStringLiteral("在线识别"),
                QStringLiteral("在线识别会把当前选区图片发送到你配置的视觉模型服务。\n"
                               "本地模型始终可用，是否允许联网识别？"),
                QMessageBox::Yes | QMessageBox::No, QMessageBox::No);
            if (ans != QMessageBox::Yes) { err = QStringLiteral("已取消联网识别"); return false; }
            cfg.ocrPrivacyAccepted = true;
            cfg.save();
        }
        ProviderPreset vp = visionPreset();
        QString key = secrets::load("vision_api_key_" + cfg.visionProvider);
        if (key.isEmpty()) key = secrets::load("translate_api_key_" + cfg.visionProvider);
        if (key.isEmpty()) {
            err = QStringLiteral("还没有配置视觉模型的 API Key（设置 → 识别）");
            return false;
        }
        QString prompt = cfg.ocrFormula
            ? QStringLiteral("识别这张图片中的全部文字和数学公式。公式用 LaTeX 表示并用 $ 包裹。"
                             "按原版面逐行输出，不要解释，不要编造。")
            : QStringLiteral("识别这张图片中的全部文字，按原版面逐行输出，不要解释，不要编造。");

        QElapsedTimer t; t.start();
        VisionClient vc;
        VisionResult r = vc.recognize(img, prompt, vp.baseUrl, vp.model, key);
        elapsed = t.elapsed();
        if (!r.ok) { err = r.error; return false; }

        lines.clear();
        const QStringList rows = r.text.split('\n');
        for (const QString& row : rows) {
            const QString t2 = row.trimmed();
            if (t2.isEmpty()) continue;
            OcrLine l;
            l.text = t2;
            l.score = 1.0f;
            l.box = QRect();          // 在线结果没有像素框
            lines.append(l);
        }
        usedBackend = QStringLiteral("在线 %1").arg(r.model.isEmpty() ? vp.model : r.model);
        return !lines.isEmpty();
    };

    setCursor(Qt::WaitCursor);
    bool ok = false;
    if (backend == QLatin1String("online")) {
        ok = runOnline();
        if (!ok) ok = runLocal();      // 在线失败回落本地
    } else if (backend == QLatin1String("auto")) {
        ok = runLocal();
        if (!ok) ok = runOnline();
    } else {
        ok = runLocal();
    }
    unsetCursor();

    if (!ok || lines.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("文字识别"),
                             err.isEmpty() ? QStringLiteral("没有识别到文字") : err);
        return;
    }

    // ---- 组装识别结果对话框 ----
    OcrDialogInput in;
    in.image = img;
    in.lines = lines;
    in.backend = usedBackend;
    in.elapsedMs = int(elapsed);

    OcrDialog dlg(in, this);
    dlg.setSourceLang(cfg.translateSource);
    dlg.setTargetLang(cfg.translateTarget);

    QStringList modelIds;
    for (const auto& p : TranslateClient::presets()) modelIds << p.id;
    dlg.setModels(modelIds, cfg.translateProvider);

    {
        QString key = secrets::load("vision_api_key_" + cfg.visionProvider);
        if (key.isEmpty()) key = secrets::load("translate_api_key_" + cfg.visionProvider);
        dlg.setOnlineAvailable(!key.isEmpty());
    }

    // 翻译链：主引擎 +（可选）备用引擎
    auto buildChain = []() {
        QVector<QPair<ProviderPreset, QString>> chain;
        Config& c = Config::get();
        QStringList ids;
        ids << c.translateProvider;
        if (!c.translateFallbackProvider.isEmpty() && c.translateFallbackProvider != c.translateProvider)
            ids << c.translateFallbackProvider;
        for (const QString& id : ids) {
            ProviderPreset p = TranslateClient::presetById(id);
            if (id == c.translateProvider) {
                if (!c.translateBaseUrl.isEmpty()) p.baseUrl = c.translateBaseUrl;
                if (!c.translateModel.isEmpty()) p.model = c.translateModel;
            } else {
                if (!c.translateFallbackBaseUrl.isEmpty()) p.baseUrl = c.translateFallbackBaseUrl;
                if (!c.translateFallbackModel.isEmpty()) p.model = c.translateFallbackModel;
            }
            QString key = secrets::load("translate_api_key_" + id);
            if (key.isEmpty() && id == c.translateProvider) key = secrets::load("translate_api_key");
            if (key.isEmpty()) continue;
            chain.append({p, key});
        }
        return chain;
    };

    QObject::connect(&dlg, &OcrDialog::translateRequested, &dlg, [&dlg, buildChain]() {
        const QStringList rows = dlg.sourceLines();
        if (rows.isEmpty()) return;
        const auto chain = buildChain();
        if (chain.isEmpty()) {
            dlg.setStatusText(QStringLiteral("未配置翻译 API Key（设置 → 翻译）"));
            return;
        }
        const QString src = dlg.sourceLang();
        const QString tgt = dlg.targetLang();
        const QString glossary = Config::get().translateGlossary;

        dlg.setBusy(true, QStringLiteral("翻译中… 0/%1").arg(rows.size()));
        QApplication::processEvents();

        QStringList out;
        int fail = 0;
        for (int i = 0; i < rows.size(); ++i) {
            QString text = rows[i].trimmed();
            if (text.isEmpty()) { out << QString(); continue; }
            TranslateResult r;
            for (const auto& pr : chain) {
                r = TranslateClient().translateLine(text, tgt, pr.first, pr.second, glossary, src);
                if (r.ok) break;
            }
            if (r.ok) out << r.text;
            else { out << QStringLiteral("[翻译失败]"); ++fail; }
            dlg.setBusy(true, QStringLiteral("翻译中… %1/%2").arg(i + 1).arg(rows.size()));
            QApplication::processEvents();
        }
        dlg.setTranslated(out);
        dlg.setBusy(false, fail == 0 ? QStringLiteral("翻译完成")
                                     : QStringLiteral("完成，%1 行失败").arg(fail));
    });

    QObject::connect(&dlg, &OcrDialog::copyRequested, &dlg, [&dlg](const QString& text) {
        QApplication::clipboard()->setText(text);
        dlg.setStatusText(QStringLiteral("已复制到剪贴板"));
    });

    // 译图：逐行翻译后把译文渲染回原图，再钉到屏幕上
    QImage pinImg;
    bool pinPending = false;
    QObject::connect(&dlg, &OcrDialog::imageTranslateRequested, &dlg, [&dlg, &pinImg, &pinPending, buildChain, img, lines]() {
        if (lines.isEmpty() || lines.first().box.isNull()) {
            dlg.setStatusText(QStringLiteral("在线识别结果没有像素位置，无法译图"));
            return;
        }
        const auto chain = buildChain();
        if (chain.isEmpty()) {
            dlg.setStatusText(QStringLiteral("未配置翻译 API Key（设置 → 翻译）"));
            return;
        }
        const QString src = dlg.sourceLang();
        const QString tgt = dlg.targetLang();
        const QString glossary = Config::get().translateGlossary;

        dlg.setBusy(true, QStringLiteral("译图中…"));
        QApplication::processEvents();

        QStringList translated;
        int okCount = 0;
        for (int i = 0; i < lines.size(); ++i) {
            TranslateResult r;
            for (const auto& pr : chain) {
                r = TranslateClient().translateLine(lines[i].text, tgt, pr.first, pr.second, glossary, src);
                if (r.ok) break;
            }
            translated << (r.ok ? r.text : QString());
            if (r.ok) ++okCount;
            dlg.setBusy(true, QStringLiteral("译图中… %1/%2").arg(i + 1).arg(lines.size()));
            QApplication::processEvents();
        }
        dlg.setBusy(false, QStringLiteral("译图完成"));
        if (okCount == 0) return;

        pinImg = renderTranslated(img, lines, translated);
        pinPending = true;
        dlg.accept();
    });

    dlg.exec();

    if (pinPending) {
        emit pinRequested(pinImg);
        close();
        emit closed();
    }
}

'''
s = s[:start] + new + s[end:]

if '#include "ocrdialog.h"' not in s:
    s = s.replace('#include "ocr.h"', '#include "ocr.h"\n#include "ocrdialog.h"\n#include "vision.h"')
if '#include <QElapsedTimer>' not in s:
    s = s.replace('#include <QFile>', '#include <QFile>\n#include <QElapsedTimer>\n#include <QApplication>\n#include <QClipboard>')
io.open(p, "w", encoding="utf-8").write(s)
print("onOcr rewritten")
