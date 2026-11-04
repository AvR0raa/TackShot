import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.cpp"
s = io.open(p, encoding="utf-8").read()

start = s.index("QWidget* SettingsDialog::makeOcrPage() {")
end = s.index("// ---------------------------------------------------------------- 录制页")
new = r'''QWidget* SettingsDialog::makeOcrPage() {
    QFormLayout* form = nullptr;
    QWidget* page = pageWrap(this, QStringLiteral("识别"),
                             QStringLiteral("文字与公式识别都走云端接口，可分别配置、互相兜底。"), form);

    form->addRow(QString(), subLabel(QStringLiteral(
        "· 文字/译图：百度翻译「图片翻译 API」——一次调用拿到原文、译文、坐标与整图贴合\n"
        "· 公式：SimpleTex——输出 LaTeX\n"
        "· 兜底：视觉大模型（OpenAI 兼容）")));

    // ---- 百度 ----
    form->addRow(QString(), titleLabel(QStringLiteral("百度图片翻译")));

    m_baiduAppId = new QLineEdit(Config::get().baiduAppId, this);
    m_baiduAppId->setPlaceholderText(QStringLiteral("开放平台控制台的 APPID"));
    form->addRow(QStringLiteral("APPID"), m_baiduAppId);
    connect(m_baiduAppId, &QLineEdit::textEdited, this, [this]() { scheduleApply(); });

    m_baiduSecret = new QLineEdit(this);
    m_baiduSecret->setEchoMode(QLineEdit::Password);
    m_baiduSecret->setPlaceholderText(QStringLiteral("密钥（DPAPI 加密保存）"));
    if (!secrets::load("baidu_secret").isEmpty()) m_baiduSecret->setText(secrets::load("baidu_secret"));
    form->addRow(QStringLiteral("密钥"), m_baiduSecret);
    connect(m_baiduSecret, &QLineEdit::textEdited, this, [this]() { scheduleApply(); });

    m_baiduPaste = new QComboBox(this);
    m_baiduPaste->addItem(QStringLiteral("整图贴合（推荐，返回翻译好的整张图）"), 1);
    m_baiduPaste->addItem(QStringLiteral("分块贴合（返回每块的小图）"), 2);
    m_baiduPaste->addItem(QStringLiteral("关闭贴合（只要文字和坐标）"), 0);
    {
        int idx = m_baiduPaste->findData(Config::get().baiduPaste);
        m_baiduPaste->setCurrentIndex(idx >= 0 ? idx : 0);
    }
    form->addRow(QStringLiteral("贴合"), m_baiduPaste);
    connect(m_baiduPaste, &QComboBox::currentIndexChanged, this, [this]() { scheduleApply(); });

    auto* baiduHint = subLabel(QStringLiteral(
        "免费额度：每月 1000 次。图片限制：png/jpg、≤4MB、最短边 ≥30、最长边 ≤4096。"));
    form->addRow(QString(), baiduHint);

    // ---- SimpleTex ----
    form->addRow(QString(), titleLabel(QStringLiteral("SimpleTex（数学公式）")));

    m_simpleTexToken = new QLineEdit(this);
    m_simpleTexToken->setEchoMode(QLineEdit::Password);
    m_simpleTexToken->setPlaceholderText(QStringLiteral("用户中心 → 用户授权 Token（UAT）"));
    if (!secrets::load("simpletex_token").isEmpty())
        m_simpleTexToken->setText(secrets::load("simpletex_token"));
    form->addRow(QStringLiteral("Token"), m_simpleTexToken);
    connect(m_simpleTexToken, &QLineEdit::textEdited, this, [this]() { scheduleApply(); });

    form->addRow(QString(), subLabel(QStringLiteral(
        "轻量模型 ¥0.04/次，每日赠送 2000 次免费调用；识别结果直接填入 LaTeX 页。")));

    // ---- 视觉大模型兜底 ----
    form->addRow(QString(), titleLabel(QStringLiteral("视觉大模型（兜底）")));

    m_visionProvider = new QComboBox(this);
    for (const auto& p : TranslateClient::presets()) m_visionProvider->addItem(p.name, p.id);
    {
        int idx = m_visionProvider->findData(Config::get().visionProvider);
        m_visionProvider->setCurrentIndex(idx >= 0 ? idx : 0);
    }
    form->addRow(QStringLiteral("引擎"), m_visionProvider);

    m_visionBase = new QLineEdit(Config::get().visionBaseUrl, this);
    m_visionBase->setPlaceholderText(QStringLiteral("留空使用预设地址"));
    m_visionModel = new QLineEdit(Config::get().visionModel, this);
    m_visionModel->setPlaceholderText(QStringLiteral("例如 gemini-3.8-flash / qwen-vl-max"));
    m_visionKey = new QLineEdit(this);
    m_visionKey->setEchoMode(QLineEdit::Password);
    m_visionKey->setPlaceholderText(QStringLiteral("视觉模型的 API Key（可留空）"));
    {
        QString vid = Config::get().visionProvider;
        QString vk = secrets::load("vision_api_key_" + vid);
        if (!vk.isEmpty()) m_visionKey->setText(vk);
    }
    form->addRow(QStringLiteral("Base URL"), m_visionBase);
    form->addRow(QStringLiteral("模型"), m_visionModel);
    form->addRow(QStringLiteral("API Key"), m_visionKey);

    connect(m_visionBase, &QLineEdit::textEdited, this, [this]() { scheduleApply(); });
    connect(m_visionModel, &QLineEdit::textEdited, this, [this]() { scheduleApply(); });
    connect(m_visionKey, &QLineEdit::textEdited, this, [this]() { scheduleApply(); });

    m_visionStatus = new QLabel(this);
    m_visionStatus->setObjectName(QStringLiteral("tsSub"));
    m_visionStatus->setWordWrap(true);
    auto* probeBtn = new QPushButton(QStringLiteral("测试图片能力"), this);
    probeBtn->setObjectName(QStringLiteral("tsProbeVision"));
    connect(probeBtn, &QPushButton::clicked, this, [this]() {
        m_visionStatus->setText(QStringLiteral("测试中…"));
        QApplication::processEvents();
        ProviderPreset vp = TranslateClient::presetById(m_visionProvider->currentData().toString());
        const QString base = m_visionBase->text().trimmed().isEmpty() ? vp.baseUrl : m_visionBase->text().trimmed();
        const QString model = m_visionModel->text().trimmed().isEmpty() ? vp.model : m_visionModel->text().trimmed();
        QString key = m_visionKey->text().trimmed();
        if (key.isEmpty()) key = secrets::load("vision_api_key_" + m_visionProvider->currentData().toString());
        if (key.isEmpty()) { m_visionStatus->setText(QStringLiteral("请先填写 API Key")); return; }
        VisionClient vc;
        auto r = vc.probe(base, model, key);
        m_visionStatus->setText(r.ok ? QStringLiteral("图片能力正常：%1").arg(r.text.left(30))
                                     : QStringLiteral("失败：%1").arg(r.error));
    });
    auto* probeRow = new QHBoxLayout;
    probeRow->addWidget(probeBtn);
    probeRow->addWidget(m_visionStatus, 1);
    form->addRow(QString(), probeRow);

    form->addRow(QString(), subLabel(QStringLiteral(
        "百度未配置时，文字识别会自动回退到视觉大模型（只有文字，没有坐标）。")));
    return page;
}

'''
s = s[:start] + new + s[end:]

# applyNow：保存百度 / SimpleTex 配置
s = s.replace("""    if (m_ocrBackend) c.ocrBackend = m_ocrBackend->currentData().toString();
    if (m_ocrFormula) c.ocrFormula = m_ocrFormula->isChecked();""",
"""    if (m_ocrFormula) c.ocrFormula = m_ocrFormula->isChecked();
    if (m_baiduAppId) c.baiduAppId = m_baiduAppId->text().trimmed();
    if (m_baiduPaste) c.baiduPaste = m_baiduPaste->currentData().toInt();
    if (m_baiduSecret && !m_baiduSecret->text().trimmed().isEmpty())
        secrets::save("baidu_secret", m_baiduSecret->text().trimmed());
    if (m_simpleTexToken && !m_simpleTexToken->text().trimmed().isEmpty())
        secrets::save("simpletex_token", m_simpleTexToken->text().trimmed());""")
io.open(p, "w", encoding="utf-8").write(s)

# 头文件：新成员
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.h"
s = io.open(p, encoding="utf-8").read()
if "m_baiduAppId" not in s:
    s = s.replace("""    QComboBox*        m_ocrBackend = nullptr;
    QCheckBox*        m_ocrFormula = nullptr;""",
"""    QCheckBox*        m_ocrFormula = nullptr;
    QLineEdit*        m_baiduAppId = nullptr;
    QLineEdit*        m_baiduSecret = nullptr;
    QComboBox*        m_baiduPaste = nullptr;
    QLineEdit*        m_simpleTexToken = nullptr;""")
    io.open(p, "w", encoding="utf-8").write(s)
print("settings OCR page rebuilt for cloud")
