import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()

start = s.index("void Overlay::onOcr() {")
end = s.index("void Overlay::onLongShot() {")
new = r'''// 中文语言名 -> 百度语言码
static QString toBaiduLang(const QString& name) {
    const QString s = name.trimmed();
    if (s.isEmpty() || s.contains(QStringLiteral("自动"))) return QStringLiteral("auto");
    if (s.contains(QStringLiteral("英"))) return QStringLiteral("en");
    if (s.contains(QStringLiteral("日"))) return QStringLiteral("jp");
    if (s.contains(QStringLiteral("韩")) || s.contains(QStringLiteral("韓"))) return QStringLiteral("kor");
    if (s.contains(QStringLiteral("繁"))) return QStringLiteral("cht");
    if (s.contains(QStringLiteral("中"))) return QStringLiteral("zh");
    if (s.contains(QStringLiteral("法"))) return QStringLiteral("fra");
    if (s.contains(QStringLiteral("德"))) return QStringLiteral("de");
    if (s.contains(QStringLiteral("俄"))) return QStringLiteral("ru");
    if (s.contains(QStringLiteral("西"))) return QStringLiteral("spa");
    if (s.contains(QStringLiteral("葡"))) return QStringLiteral("pt");
    if (s.contains(QStringLiteral("意"))) return QStringLiteral("it");
    return QStringLiteral("auto");
}

void Overlay::onOcr() {
    QImage img = selectionImage(false);
    if (img.isNull()) return;

    Config& cfg = Config::get();
    const bool baiduReady = !cfg.baiduAppId.trimmed().isEmpty() &&
                            !secrets::load("baidu_secret").isEmpty();
    const QString stToken = secrets::load("simpletex_token");
    const bool stReady = !stToken.isEmpty();
    const bool visionReady = !secrets::load("vision_api_key_" + cfg.visionProvider).isEmpty();

    if (!baiduReady && !stReady && !visionReady) {
        QMessageBox::information(this, QStringLiteral("识别"),
            QStringLiteral("还没有配置任何识别服务。\n\n"
                           "请到 托盘菜单 → 设置 → 识别 里填写：\n"
                           "· 百度翻译 APPID / 密钥（文字 + 图片翻译）\n"
                           "· SimpleTex Token（公式识别）\n"
                           "· 或视觉大模型的 API Key"));
        return;
    }

    if (!cfg.ocrPrivacyAccepted) {
        const auto ans = QMessageBox::question(
            this, QStringLiteral("在线识别"),
            QStringLiteral("识别会把当前选区图片上传到你配置的云端服务"
                           "（百度翻译 / SimpleTex / 视觉大模型）。\n\n是否继续？"),
            QMessageBox::Yes | QMessageBox::No, QMessageBox::Yes);
        if (ans != QMessageBox::Yes) return;
        cfg.ocrPrivacyAccepted = true;
        cfg.save();
    }

    QVector<OcrLine> lines;
    QStringList translated;
    QImage pasteImg;
    QString usedBackend;
    QString err;
    qint64 elapsed = 0;

    setCursor(Qt::WaitCursor);
    QCoreApplication::processEvents();

    // ---- 公式：SimpleTex ----
    QString latex;
    if (cfg.ocrFormula && stReady) {
        QElapsedTimer t; t.start();
        SimpleTexClient st;
        auto r = st.recognize(img, stToken, true);
        elapsed += t.elapsed();
        if (r.ok) latex = r.latex;
        else if (err.isEmpty()) err = r.error;
    }

    // ---- 文字 + 翻译：百度图片翻译 ----
    if (baiduReady) {
        QElapsedTimer t; t.start();
        BaiduPictureTranslate bd;
        auto r = bd.translate(img, QStringLiteral("auto"), toBaiduLang(cfg.translateTarget),
                              cfg.baiduAppId, secrets::load("baidu_secret"), cfg.baiduPaste);
        elapsed += t.elapsed();
        if (r.ok) {
            for (const auto& l : r.lines) {
                OcrLine o;
                o.text = l.src;
                o.score = 1.0f;
                o.box = l.rect;
                lines.append(o);
                translated << l.dst;
            }
            pasteImg = r.pasteImage;
            usedBackend = QStringLiteral("百度图片翻译");
        } else if (err.isEmpty()) {
            err = r.error;
        }
    }

    // ---- 兜底：视觉大模型（只有文字，没有坐标）----
    if (lines.isEmpty() && visionReady) {
        ProviderPreset vp = TranslateClient::presetById(cfg.visionProvider);
        if (!cfg.visionBaseUrl.isEmpty()) vp.baseUrl = cfg.visionBaseUrl;
        if (!cfg.visionModel.isEmpty()) vp.model = cfg.visionModel;
        const QString key = secrets::load("vision_api_key_" + cfg.visionProvider);
        QString prompt = cfg.ocrFormula
            ? QStringLiteral("识别图片里的文字和数学公式，公式用 LaTeX 并用 $ 包裹，按行输出，不要解释。")
            : QStringLiteral("识别图片里的全部文字，按行输出，不要解释。");
        QElapsedTimer t; t.start();
        VisionClient vc;
        auto r = vc.recognize(img, prompt, vp.baseUrl, vp.model, key);
        elapsed += t.elapsed();
        if (r.ok) {
            for (const QString& row : r.text.split('\n')) {
                const QString q = row.trimmed();
                if (q.isEmpty()) continue;
                OcrLine o; o.text = q; o.score = 1.0f; o.box = QRect();
                lines.append(o);
            }
            usedBackend = QStringLiteral("视觉大模型 %1").arg(r.model.isEmpty() ? vp.model : r.model);
        } else if (err.isEmpty()) {
            err = r.error;
        }
    }

    unsetCursor();

    if (lines.isEmpty() && latex.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("识别"),
                             err.isEmpty() ? QStringLiteral("没有识别到内容") : err);
        return;
    }

    OcrDialogInput in;
    in.image = img;
    in.lines = lines;
    in.backend = usedBackend.isEmpty() ? QStringLiteral("公式识别") : usedBackend;
    in.elapsedMs = int(elapsed);

    OcrDialog dlg(in, this);
    dlg.setSourceLang(cfg.translateSource);
    dlg.setTargetLang(cfg.translateTarget);
    {
        QStringList ids;
        for (const auto& p : TranslateClient::presets()) ids << p.id;
        dlg.setModels(ids, cfg.translateProvider);
    }
    {
        bool anyKey = !secrets::load("translate_api_key").isEmpty();
        if (!anyKey) {
            for (const auto& p : TranslateClient::presets()) {
                if (!secrets::load("translate_api_key_" + p.id).isEmpty()) { anyKey = true; break; }
            }
        }
        dlg.setOnlineAvailable(anyKey);
    }

    if (!translated.isEmpty() && translated.size() == lines.size()) dlg.setTranslated(translated);
    if (!latex.isEmpty()) {
        dlg.setLatex(latex);
        if (auto* tabs = dlg.findChild<QTabWidget*>()) tabs->setCurrentIndex(0);
    }

    // 手动翻译（可选）：走翻译 API，逐行覆盖译文页
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
            const QString text = rows[i].trimmed();
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

    // 译图：优先用百度返回的整图贴合结果；否则按坐标本地回填
    QImage pinImg;
    bool pinPending = false;
    QObject::connect(&dlg, &OcrDialog::imageTranslateRequested, &dlg,
                     [&dlg, &pinImg, &pinPending, pasteImg, img, lines, buildChain]() {
        if (!pasteImg.isNull()) {
            pinImg = pasteImg;
            pinPending = true;
            dlg.accept();
            return;
        }
        if (lines.isEmpty() || lines.first().box.isNull()) {
            dlg.setStatusText(QStringLiteral("当前结果没有坐标，无法回填；可改用百度图片翻译"));
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
if '#include "baidu.h"' not in s:
    s = s.replace('#include "vision.h"', '#include "vision.h"\n#include "baidu.h"\n#include "simpletex.h"')
io.open(p, "w", encoding="utf-8").write(s)
print("onOcr rewritten for cloud providers")
