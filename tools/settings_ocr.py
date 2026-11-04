import io

# ---------------- settingsdialog.h ----------------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.h"
s = io.open(p, encoding="utf-8").read()
if "makeOcrPage" not in s:
    s = s.replace("    QWidget* makeShotPage();", "    QWidget* makeShotPage();\n    QWidget* makeOcrPage();")
if "m_trSource" not in s:
    s = s.replace("    QComboBox*        m_trTarget = nullptr;",
                  "    QComboBox*        m_trSource = nullptr;\n    QComboBox*        m_trTarget = nullptr;")
if "m_ocrBackend" not in s:
    s = s.replace("    QComboBox*        m_appearance = nullptr;",
'''    QComboBox*        m_ocrBackend = nullptr;
    QCheckBox*        m_ocrFormula = nullptr;
    QComboBox*        m_visionProvider = nullptr;
    QLineEdit*        m_visionBase = nullptr;
    QLineEdit*        m_visionModel = nullptr;
    QLineEdit*        m_visionKey = nullptr;
    QLabel*           m_visionStatus = nullptr;

    QComboBox*        m_appearance = nullptr;''')
io.open(p, "w", encoding="utf-8").write(s)

# ---------------- settingsdialog.cpp ----------------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.cpp"
s = io.open(p, encoding="utf-8").read()

# 1) 导航加「识别」
s = s.replace("""    m_pages->addWidget(makeShotPage());
    m_pages->addWidget(makeRecordPage());""",
"""    m_pages->addWidget(makeShotPage());
    m_pages->addWidget(makeOcrPage());
    m_pages->addWidget(makeRecordPage());""")
s = s.replace("""    const QStringList navNames = {QStringLiteral("截图"), QStringLiteral("录制"),
                                  QStringLiteral("翻译"), QStringLiteral("外观与其他")};""",
"""    const QStringList navNames = {QStringLiteral("截图"), QStringLiteral("识别"),
                                  QStringLiteral("录制"), QStringLiteral("翻译"),
                                  QStringLiteral("外观与其他")};""")

# 2) 翻译页：源语言
s = s.replace("""    m_trTarget = new QComboBox(this);
    m_trTarget->setEditable(true);
    m_trTarget->addItems({"简体中文", "繁體中文", "English", "日本語", "한국어",
                          "Français", "Deutsch", "Español", "Русский"});
    m_trTarget->setCurrentText(Config::get().translateTarget);""",
"""    m_trTarget = new QComboBox(this);
    m_trTarget->setEditable(true);
    m_trTarget->addItems({"简体中文", "繁體中文", "English", "日本語", "한국어",
                          "Français", "Deutsch", "Español", "Русский"});
    m_trTarget->setCurrentText(Config::get().translateTarget);

    m_trSource = new QComboBox(this);
    m_trSource->setEditable(true);
    m_trSource->addItems({"English", "自动检测", "简体中文", "繁體中文", "日本語", "한국어",
                          "Français", "Deutsch", "Español", "Русский"});
    m_trSource->setCurrentText(Config::get().translateSource);""")
s = s.replace("""    form->addRow(QStringLiteral("API Key"), m_trKey);
    form->addRow(QStringLiteral("目标语言"), m_trTarget);""",
"""    form->addRow(QStringLiteral("API Key"), m_trKey);
    form->addRow(QStringLiteral("源语言"), m_trSource);
    form->addRow(QStringLiteral("目标语言"), m_trTarget);""")
s = s.replace("    connect(m_trTarget, &QComboBox::currentTextChanged, this, [this]() { scheduleApply(); });",
"""    connect(m_trTarget, &QComboBox::currentTextChanged, this, [this]() { scheduleApply(); });
    connect(m_trSource, &QComboBox::currentTextChanged, this, [this]() { scheduleApply(); });""")

# 3) 识别页（在 makeRecordPage 之前插入）
anchor = "// ---------------------------------------------------------------- 录制页"
ocr_page = r'''// ---------------------------------------------------------------- 识别页
QWidget* SettingsDialog::makeOcrPage() {
    QFormLayout* form = nullptr;
    QWidget* page = pageWrap(this, QStringLiteral("识别"),
                             QStringLiteral("文字与公式识别：本地模型始终可用，联网时可走视觉大模型。"), form);

    m_ocrBackend = new QComboBox(this);
    m_ocrBackend->addItem(QStringLiteral("仅本地（离线，PP-OCR + 公式模型）"), QStringLiteral("local"));
    m_ocrBackend->addItem(QStringLiteral("本地优先（复杂版面/低置信度时联网）"), QStringLiteral("auto"));
    m_ocrBackend->addItem(QStringLiteral("仅在线（视觉大模型）"), QStringLiteral("online"));
    {
        int idx = m_ocrBackend->findData(Config::get().ocrBackend);
        m_ocrBackend->setCurrentIndex(idx >= 0 ? idx : 0);
    }
    form->addRow(QStringLiteral("识别方式"), m_ocrBackend);
    connect(m_ocrBackend, &QComboBox::currentIndexChanged, this, [this]() { scheduleApply(); });

    m_ocrFormula = new QCheckBox(QStringLiteral("识别数学公式（输出 LaTeX）"), this);
    m_ocrFormula->setChecked(Config::get().ocrFormula);
    form->addRow(QString(), m_ocrFormula);
    connect(m_ocrFormula, &QCheckBox::toggled, this, [this]() { scheduleApply(); });

    form->addRow(QString(), subLabel(QStringLiteral(
        "在线识别使用 OpenAI 兼容的视觉接口（图片以 data URL 发送）， Key 与翻译的 Key 分开保存。")));

    m_visionProvider = new QComboBox(this);
    for (const auto& p : TranslateClient::presets()) m_visionProvider->addItem(p.name, p.id);
    {
        int idx = m_visionProvider->findData(Config::get().visionProvider);
        m_visionProvider->setCurrentIndex(idx >= 0 ? idx : 0);
    }
    form->addRow(QStringLiteral("视觉引擎"), m_visionProvider);

    m_visionBase = new QLineEdit(Config::get().visionBaseUrl, this);
    m_visionBase->setPlaceholderText(QStringLiteral("留空使用预设地址"));
    m_visionModel = new QLineEdit(Config::get().visionModel, this);
    m_visionModel->setPlaceholderText(QStringLiteral("例如 gemini-3.8-flash / qwen-vl-max"));
    m_visionKey = new QLineEdit(this);
    m_visionKey->setEchoMode(QLineEdit::Password);
    m_visionKey->setPlaceholderText(QStringLiteral("视觉模型的 API Key（可留空）"));
    if (secretsLoaded()) {}

    form->addRow(QStringLiteral("Base URL"), m_visionBase);
    form->addRow(QStringLiteral("模型"), m_visionModel);
    form->addRow(QStringLiteral("API Key"), m_visionKey);

    connect(m_visionBase, &QLineEdit::textEdited, this, [this]() { scheduleApply(); });
    connect(m_visionModel, &QLineEdit::textEdited, this, [this]() { scheduleApply(); });
    connect(m_visionKey, &QLineEdit::textEdited, this, [this]() { scheduleApply(); });
    connect(m_visionProvider, &QComboBox::currentIndexChanged, this, [this]() {
        auto fill = [this]() {
            ProviderPreset p = TranslateClient::presetById(m_visionProvider->currentData().toString());
            if (m_visionBase->text().isEmpty()) m_visionBase->setText(p.baseUrl);
            if (m_visionModel->text().isEmpty()) m_visionModel->setText(p.model);
        };
        fill();
        scheduleApply();
    });

    m_visionStatus = new QLabel(this);
    m_visionStatus->setObjectName(QStringLiteral("tsSub"));
    m_visionStatus->setWordWrap(true);
    auto* probeBtn = new QPushButton(QStringLiteral("测试图片能力"), this);
    probeBtn->setObjectName(QStringLiteral("tsProbeVision"));
    auto* probeRow = new QHBoxLayout;
    probeRow->addWidget(probeBtn);
    probeRow->addWidget(m_visionStatus, 1);
    form->addRow(QString(), probeRow);

    form->addRow(QString(), subLabel(QStringLiteral(
        "离线时不会发起任何请求；首次在线识别会再确认一次。")));
    return page;
}

'''
s = s.replace(anchor, ocr_page + anchor, 1)

# 4) applyNow 持久化新字段
s = s.replace("""    if (m_trTarget) c.translateTarget = m_trTarget->currentText().trimmed();""",
"""    if (m_trSource) c.translateSource = m_trSource->currentText().trimmed();
    if (m_trTarget) c.translateTarget = m_trTarget->currentText().trimmed();""")
s = s.replace("""    if (m_copy) c.copyAfterCapture = m_copy->isChecked();""",
"""    if (m_ocrBackend) c.ocrBackend = m_ocrBackend->currentData().toString();
    if (m_ocrFormula) c.ocrFormula = m_ocrFormula->isChecked();
    if (m_visionProvider) c.visionProvider = m_visionProvider->currentData().toString();
    if (m_visionBase) c.visionBaseUrl = m_visionBase->text().trimmed();
    if (m_visionModel) c.visionModel = m_visionModel->text().trimmed();
    if (m_visionKey) {
        QString vk = m_visionKey->text().trimmed();
        if (!vk.isEmpty()) secrets::save("vision_api_key_" + c.visionProvider, vk);
    }

    if (m_copy) c.copyAfterCapture = m_copy->isChecked();""")
io.open(p, "w", encoding="utf-8").write(s)
print("settings: OCR page + source language added")
