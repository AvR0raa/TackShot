import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()

s = s.replace('#include "sessions.h"', '#include "sessions.h"\n#include "translate.h"\n#include "secrets.h"')

start = s.index("    QDialog dlg(this);\n    dlg.setWindowTitle(QStringLiteral(\"识别结果")
end = s.index("    dlg.exec();", start) + len("    dlg.exec();")
new = '''    QDialog dlg(this);
    dlg.setWindowTitle(QStringLiteral("识别结果 — %1 行").arg(lines.size()));
    dlg.resize(620, 520);
    auto* lay = new QVBoxLayout(&dlg);

    auto* srcLabel = new QLabel(QStringLiteral("原文"), &dlg);
    lay->addWidget(srcLabel);
    auto* edit = new QPlainTextEdit(all, &dlg);
    edit->setLineWrapMode(QPlainTextEdit::WidgetWidth);
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
    lay->addWidget(status);

    auto* row = new QHBoxLayout;
    row->addStretch();
    auto* trBtn = new QPushButton(QStringLiteral("翻译"), &dlg);
    auto* copySrc = new QPushButton(QStringLiteral("复制原文"), &dlg);
    auto* copyDst = new QPushButton(QStringLiteral("复制译文"), &dlg);
    copyDst->setEnabled(false);
    auto* closeBtn = new QPushButton(QStringLiteral("关闭"), &dlg);
    row->addWidget(trBtn);
    row->addWidget(copySrc);
    row->addWidget(copyDst);
    row->addWidget(closeBtn);
    lay->addLayout(row);

    connect(copySrc, &QPushButton::clicked, [&]() {
        QApplication::clipboard()->setText(edit->toPlainText());
    });
    connect(copyDst, &QPushButton::clicked, [&]() {
        QApplication::clipboard()->setText(dst->toPlainText());
    });
    connect(closeBtn, &QPushButton::clicked, &dlg, &QDialog::reject);

    connect(trBtn, &QPushButton::clicked, [&]() {
        Config& cfg = Config::get();
        QString key = secrets::load("translate_api_key");
        if (key.isEmpty()) {
            QMessageBox::information(&dlg, QStringLiteral("翻译"),
                QStringLiteral("还没有配置 API Key。\\n请到托盘菜单 → 设置 → 翻译 里填写。"));
            return;
        }
        if (!cfg.translatePrivacyAccepted) {
            auto r = QMessageBox::question(&dlg, QStringLiteral("翻译"),
                QStringLiteral("将把 %1 个字符发送到翻译服务（%2）。\\n是否继续？")
                    .arg(edit->toPlainText().size()).arg(cfg.translateBaseUrl),
                QMessageBox::Yes | QMessageBox::No);
            if (r != QMessageBox::Yes) return;
            cfg.translatePrivacyAccepted = true;
            cfg.save();
        }

        ProviderPreset p = TranslateClient::presetById(cfg.translateProvider);
        if (!cfg.translateBaseUrl.isEmpty()) p.baseUrl = cfg.translateBaseUrl;
        if (!cfg.translateModel.isEmpty()) p.model = cfg.translateModel;

        trBtn->setEnabled(false);
        status->setText(QStringLiteral("翻译中…（%1 / %2）").arg(cfg.translateProvider, p.model));
        QApplication::processEvents();

        TranslateClient client;
        TranslateResult r = client.translate(edit->toPlainText(), cfg.translateTarget, p, key);

        trBtn->setEnabled(true);
        if (r.ok) {
            dst->setPlainText(r.text);
            dstLabel->show();
            dst->show();
            copyDst->setEnabled(true);
            status->setText(QStringLiteral("完成 · %1 · %2 · %3 次请求")
                                .arg(r.providerId, r.model).arg(r.attempts));
        } else {
            status->setText(QStringLiteral("失败：%1").arg(r.error));
        }
    });

    dlg.exec();'''
s = s[:start] + new + s[end:]
io.open(p, "w", encoding="utf-8").write(s)
print("ocr dialog translation wired")
