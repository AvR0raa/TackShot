import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()

start = s.index("void Overlay::onOcr() {")
end = s.index("void Overlay::onLongShot()")
new = r'''// 按选区尺寸把译文渲染回原图（图片翻译）
static QImage renderTranslation(const QImage& base, const QVector<OcrLine>& lines,
                                const QStringList& translated) {
    QImage out = base.convertToFormat(QImage::Format_ARGB32);
    QPainter p(&out);
    p.setRenderHint(QPainter::TextAntialiasing, true);
    for (int i = 0; i < lines.size() && i < translated.size(); ++i) {
        if (translated[i].trimmed().isEmpty()) continue;
        QRect r = lines[i].box.adjusted(-2, -2, 2, 2).intersected(out.rect());
        if (r.width() < 6 || r.height() < 6) continue;

        // 背景色：取框内四角的众数近似（简单取平均）
        long long sr = 0, sg = 0, sb = 0; int n = 0;
        for (int dx = 0; dx < 6; ++dx)
            for (int dy = 0; dy < 6; ++dy) {
                int x = qBound(0, r.left() + dx, out.width() - 1);
                int y = qBound(0, r.top() + dy, out.height() - 1);
                QRgb c = out.pixel(x, y);
                sr += qRed(c); sg += qGreen(c); sb += qBlue(c); n++;
            }
        QColor bg(int(sr / n), int(sg / n), int(sb / n));
        QColor fg = (bg.lightnessF() > 0.55) ? QColor(20, 20, 20) : QColor(240, 240, 240);

        p.fillRect(r, bg);

        QFont f(QStringLiteral("Microsoft YaHei"));
        int px = qMax(9, int(r.height() * 0.78));
        f.setPixelSize(px);
        QFontMetrics fm(f);
        while (px > 7 && fm.horizontalAdvance(translated[i]) > r.width()) {
            px -= 1;
            f.setPixelSize(px);
            fm = QFontMetrics(f);
        }
        p.setFont(f);
        p.setPen(fg);
        p.drawText(r, Qt::AlignLeft | Qt::AlignVCenter, translated[i]);
    }
    p.end();
    return out;
}

void Overlay::onOcr() {
    QImage img = selectionImage(false);
    if (img.isNull()) return;
    setCursor(Qt::WaitCursor);
    QString err;
    Ocr& ocr = Ocr::get();
    QVector<OcrLine> lines;
    if (ocr.init(&err))
        lines = ocr.recognize(img, &err);
    unsetCursor();
    if (lines.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("文字识别"),
                             err.isEmpty() ? QStringLiteral("没有识别到文字") : err);
        return;
    }

    QString all;
    for (const auto& l : lines) all += l.text + "\n";

    // 组装 provider 链：主 + 备用（各自有自己的 key）
    auto buildChain = []() {
        QVector<QPair<ProviderPreset, QString>> chain;
        Config& cfg = Config::get();
        QStringList ids;
        ids << cfg.translateProvider;
        if (!cfg.translateFallbackProvider.isEmpty() && cfg.translateFallbackProvider != cfg.translateProvider)
            ids << cfg.translateFallbackProvider;
        for (const QString& id : ids) {
            ProviderPreset p = TranslateClient::presetById(id);
            if (id == cfg.translateProvider) {
                if (!cfg.translateBaseUrl.isEmpty()) p.baseUrl = cfg.translateBaseUrl;
                if (!cfg.translateModel.isEmpty()) p.model = cfg.translateModel;
            } else {
                if (!cfg.translateFallbackBaseUrl.isEmpty()) p.baseUrl = cfg.translateFallbackBaseUrl;
                if (!cfg.translateFallbackModel.isEmpty()) p.model = cfg.translateFallbackModel;
            }
            QString key = secrets::load("translate_api_key_" + id);
            if (key.isEmpty() && id == cfg.translateProvider) key = secrets::load("translate_api_key");
            if (key.isEmpty()) continue;
            chain.append({p, key});
        }
        return chain;
    };

    QDialog dlg(this);
    dlg.setWindowTitle(QStringLiteral("识别结果 — %1 行").arg(lines.size()));
    dlg.resize(640, 560);
    auto* lay = new QVBoxLayout(&dlg);

    lay->addWidget(new QLabel(QStringLiteral("原文"), &dlg));
    auto* edit = new QPlainTextEdit(all, &dlg);
    QFont f(QStringLiteral("Microsoft YaHei"));
    f.setPixelSize(14);
    edit->setFont(f);
    lay->addWidget(edit, 1);

    auto* dstLabel = new QLabel(QStringLiteral("译文"), &dlg);
    dstLabel->hide();
    lay->addWidget(dstLabel);
    auto* dst = new QPlainTextEdit(&dlg);
    dst->setReadOnly(true);
    dst->setFont(f);
    dst->hide();
    lay->addWidget(dst, 1);

    auto* status = new QLabel(&dlg);
    status->setStyleSheet("color:#888;");
    status->setWordWrap(true);
    lay->addWidget(status);

    auto* row = new QHBoxLayout;
    row->addStretch();
    auto* trBtn = new QPushButton(QStringLiteral("翻译"), &dlg);
    auto* trImgBtn = new QPushButton(QStringLiteral("译图"), &dlg);
    auto* copySrc = new QPushButton(QStringLiteral("复制原文"), &dlg);
    auto* copyDst = new QPushButton(QStringLiteral("复制译文"), &dlg);
    copyDst->setEnabled(false);
    auto* closeBtn = new QPushButton(QStringLiteral("关闭"), &dlg);
    for (auto* b : {trBtn, trImgBtn, copySrc, copyDst, closeBtn}) row->addWidget(b);
    lay->addLayout(row);

    connect(copySrc, &QPushButton::clicked, [&]() { QApplication::clipboard()->setText(edit->toPlainText()); });
    connect(copyDst, &QPushButton::clicked, [&]() { QApplication::clipboard()->setText(dst->toPlainText()); });
    connect(closeBtn, &QPushButton::clicked, &dlg, &QDialog::reject);

    // 翻译整段（分块 + 缓存 + 术语表 + 降级）
    connect(trBtn, &QPushButton::clicked, [&]() {
        Config& cfg = Config::get();
        auto chain = buildChain();
        if (chain.isEmpty()) {
            QMessageBox::information(&dlg, QStringLiteral("翻译"),
                QStringLiteral("还没有配置 API Key。\n请到托盘菜单 → 设置 → 翻译 里填写。"));
            return;
        }
        if (!cfg.translatePrivacyAccepted) {
            auto r = QMessageBox::question(&dlg, QStringLiteral("翻译"),
                QStringLiteral("将把 %1 个字符发送到翻译服务（%2）。\n是否继续？")
                    .arg(edit->toPlainText().size()).arg(chain.first().first.baseUrl),
                QMessageBox::Yes | QMessageBox::No);
            if (r != QMessageBox::Yes) return;
            cfg.translatePrivacyAccepted = true;
            cfg.save();
        }

        trBtn->setEnabled(false);
        trImgBtn->setEnabled(false);
        TranslateClient client;
        TranslateResult best;
        for (int i = 0; i < chain.size(); ++i) {
            status->setText(QStringLiteral("翻译中…（%1 / %2）")
                                .arg(chain[i].first.id, chain[i].first.model));
            QApplication::processEvents();
            best = client.translateLong(edit->toPlainText(), cfg.translateTarget,
                                        chain[i].first, chain[i].second,
                                        cfg.translateGlossary, cfg.translateChunkChars);
            if (best.ok) break;
            if (i + 1 < chain.size())
                status->setText(QStringLiteral("%1 失败（%2），切换备用…").arg(chain[i].first.id, best.error));
        }
        trBtn->setEnabled(true);
        trImgBtn->setEnabled(true);

        if (best.ok) {
            dst->setPlainText(best.text);
            dstLabel->show();
            dst->show();
            copyDst->setEnabled(true);
            status->setText(QStringLiteral("完成 · %1 · %2 · %3 段%4")
                                .arg(best.providerId, best.model).arg(best.chunkCount)
                                .arg(best.fromCache ? QStringLiteral(" · 命中缓存") : QString()));
        } else {
            status->setText(QStringLiteral("失败：%1").arg(best.error));
        }
    });

    // 译图：逐行翻译后把译文渲染回原图，再作为贴图钉住
    connect(trImgBtn, &QPushButton::clicked, [&]() {
        Config& cfg = Config::get();
        auto chain = buildChain();
        if (chain.isEmpty()) {
            QMessageBox::information(&dlg, QStringLiteral("译图"),
                QStringLiteral("还没有配置 API Key。\n请到托盘菜单 → 设置 → 翻译 里填写。"));
            return;
        }
        trBtn->setEnabled(false);
        trImgBtn->setEnabled(false);
        QStringList translated;
        bool anyOk = false;
        for (int i = 0; i < lines.size(); ++i) {
            status->setText(QStringLiteral("译图中… %1 / %2").arg(i + 1).arg(lines.size()));
            QApplication::processEvents();
            QString got;
            for (const auto& pr : chain) {
                TranslateClient c;
                auto r = c.translateLine(lines[i].text, cfg.translateTarget, pr.first, pr.second,
                                         cfg.translateGlossary);
                if (r.ok) { got = r.text; anyOk = true; break; }
            }
            translated << (got.isEmpty() ? lines[i].text : got);
        }
        trBtn->setEnabled(true);
        trImgBtn->setEnabled(true);
        if (!anyOk) {
            status->setText(QStringLiteral("译图失败：所有引擎都不可用"));
            return;
        }
        QImage composed = renderTranslation(img, lines, translated);
        emit pinRequested(composed);
        close();
        emit closed();
    });

    dlg.exec();
}

'''
s = s[:start] + new + s[end:]
io.open(p, "w", encoding="utf-8").write(s)
print("overlay translation upgraded")
