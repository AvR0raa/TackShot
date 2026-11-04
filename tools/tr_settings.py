import io

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.cpp"
s = io.open(p, encoding="utf-8").read()

s = s.replace('#include "settingsdialog.h"\n#include "config.h"',
              '#include "settingsdialog.h"\n#include "config.h"\n#include "translate.h"\n#include "secrets.h"\n#include <QLabel>')

# 在“录制音频”行之后插入翻译分组
anchor = '    form->addRow(QStringLiteral("录制音频"), m_recAudio);'
add = anchor + """

    // ---------------- 翻译 ----------------
    form->addRow(new QLabel(QStringLiteral("<b>翻译</b>"), this));

    m_trProvider = new QComboBox(this);
    for (const auto& p : TranslateClient::presets())
        m_trProvider->addItem(p.name, p.id);
    {
        int idx = m_trProvider->findData(Config::get().translateProvider);
        m_trProvider->setCurrentIndex(idx >= 0 ? idx : 0);
    }
    form->addRow(QStringLiteral("引擎"), m_trProvider);

    m_trBase = new QLineEdit(this);
    m_trModel = new QLineEdit(this);
    m_trKey = new QLineEdit(this);
    m_trKey->setEchoMode(QLineEdit::Password);
    m_trKey->setPlaceholderText(QStringLiteral("留空则不启用翻译"));

    auto applyPreset = [this](bool force) {
        QString id = m_trProvider->currentData().toString();
        ProviderPreset p = TranslateClient::presetById(id);
        if (force || m_trBase->text().isEmpty()) m_trBase->setText(p.baseUrl);
        if (force || m_trModel->text().isEmpty()) m_trModel->setText(p.model);
        if (force || m_trTarget->currentText().isEmpty()) m_trTarget->setCurrentText(Config::get().translateTarget);
    };
    connect(m_trProvider, &QComboBox::currentIndexChanged, this, [applyPreset](int) { applyPreset(true); });

    m_trTarget = new QComboBox(this);
    m_trTarget->setEditable(true);
    m_trTarget->addItems({"简体中文", "繁體中文", "English", "日本語", "한국어", "Français", "Deutsch", "Español", "Русский"});

    m_trBase->setText(Config::get().translateBaseUrl);
    m_trModel->setText(Config::get().translateModel);
    m_trTarget->setCurrentText(Config::get().translateTarget);
    applyPreset(false);

    QString saved = secrets::load("translate_api_key");
    if (!saved.isEmpty()) m_trKey->setText(saved);

    form->addRow(QStringLiteral("Base URL"), m_trBase);
    form->addRow(QStringLiteral("模型"), m_trModel);
    form->addRow(QStringLiteral("API Key"), m_trKey);
    form->addRow(QStringLiteral("目标语言"), m_trTarget);

    m_trStatus = new QLabel(this);
    m_trStatus->setStyleSheet("color:#888;");
    m_trStatus->setWordWrap(true);
    auto* testBtn = new QPushButton(QStringLiteral("测试连接"), this);
    auto* testRow = new QHBoxLayout;
    testRow->addWidget(testBtn);
    testRow->addWidget(m_trStatus, 1);
    form->addRow(QString(), testRow);

    connect(testBtn, &QPushButton::clicked, this, [this]() {
        m_trStatus->setText(QStringLiteral("测试中…"));
        QApplication::processEvents();
        ProviderPreset p;
        p.id = m_trProvider->currentData().toString();
        p.baseUrl = m_trBase->text().trimmed();
        p.model = m_trModel->text().trimmed();
        TranslateClient client;
        auto r = client.testConnection(p, m_trKey->text().trimmed());
        if (r.ok)
            m_trStatus->setText(QStringLiteral("成功：%1").arg(r.text.left(40)));
        else
            m_trStatus->setText(QStringLiteral("失败：%1").arg(r.error));
    });"""
if anchor in s:
    s = s.replace(anchor, add, 1)

# accept() 保存翻译配置
s = s.replace('    c.recordAudio = m_recAudio->currentText();',
"""    c.recordAudio = m_recAudio->currentText();
    c.translateProvider = m_trProvider->currentData().toString();
    c.translateBaseUrl = m_trBase->text().trimmed();
    c.translateModel = m_trModel->text().trimmed();
    c.translateTarget = m_trTarget->currentText().trimmed();
    {
        QString key = m_trKey->text().trimmed();
        if (!key.isEmpty()) secrets::save("translate_api_key", key);
        else secrets::remove("translate_api_key");
    }""")
io.open(p, "w", encoding="utf-8").write(s)
print("settings translation UI added")
