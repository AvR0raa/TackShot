#include "settingsdialog.h"
#include "common.h"
#include "config.h"
#include "translate.h"
#include "secrets.h"
#include "theme.h"
#include "vision.h"

#include <QLabel>
#include <QApplication>
#include <QPlainTextEdit>
#include <QSpinBox>
#include <QFormLayout>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QKeySequenceEdit>
#include <QLineEdit>
#include <QComboBox>
#include <QCheckBox>
#include <QPushButton>
#include <QFileDialog>
#include <QListWidget>
#include <QStackedWidget>
#include <QScrollArea>
#include <QSettings>
#include <QCoreApplication>
#include <QTimer>

namespace {

QLabel* titleLabel(const QString& text) {
    auto* l = new QLabel(text);
    QFont f = l->font();
    f.setPixelSize(15);
    f.setBold(true);
    l->setFont(f);
    return l;
}

QLabel* subLabel(const QString& text) {
    auto* l = new QLabel(text);
    l->setObjectName(QStringLiteral("tsSub"));
    l->setWordWrap(true);
    return l;
}

QWidget* pageWrap(QWidget* parent, const QString& title, const QString& subtitle,
                  QFormLayout*& formOut) {
    auto* page = new QWidget(parent);
    page->setObjectName(QStringLiteral("tsPage"));
    auto* lay = new QVBoxLayout(page);
    lay->setContentsMargins(22, 18, 22, 18);
    lay->setSpacing(10);
    if (!title.isEmpty()) lay->addWidget(titleLabel(title));
    if (!subtitle.isEmpty()) lay->addWidget(subLabel(subtitle));
    auto* form = new QFormLayout;
    form->setLabelAlignment(Qt::AlignLeft | Qt::AlignVCenter);
    form->setFormAlignment(Qt::AlignLeft | Qt::AlignTop);
    form->setHorizontalSpacing(18);
    form->setVerticalSpacing(10);
    form->setFieldGrowthPolicy(QFormLayout::AllNonFixedFieldsGrow);
    lay->addLayout(form);
    lay->addStretch(1);
    formOut = form;
    return page;
}

} // namespace

SettingsDialog::SettingsDialog(QWidget* parent) : QDialog(parent) {
    setWindowTitle(QStringLiteral("TackShot 设置"));
    resize(820, 580);
    setMinimumSize(760, 520);

    m_nav = new QListWidget(this);
    m_nav->setObjectName(QStringLiteral("tsNav"));
    m_nav->setFixedWidth(158);
    m_nav->setFrameShape(QFrame::NoFrame);
    m_nav->setIconSize(QSize(18, 18));

    m_pages = new QStackedWidget(this);

    m_pages->addWidget(makeShotPage());
    m_pages->addWidget(makeOcrPage());
    m_pages->addWidget(makeRecordPage());
    m_pages->addWidget(makeTranslatePage());
    m_pages->addWidget(makeOtherPage());

    const QStringList navNames = {QStringLiteral("截图"), QStringLiteral("识别"),
                                  QStringLiteral("录制"), QStringLiteral("翻译"),
                                  QStringLiteral("外观与其他")};
    for (const QString& n : navNames) m_nav->addItem(n);
    m_nav->setCurrentRow(0);
    connect(m_nav, &QListWidget::currentRowChanged, m_pages, &QStackedWidget::setCurrentIndex);

    auto* closeBtn = new QPushButton(QStringLiteral("完成"), this);
    closeBtn->setObjectName(QStringLiteral("tsPrimary"));
    closeBtn->setDefault(true);
    connect(closeBtn, &QPushButton::clicked, this, &SettingsDialog::accept);

    auto* body = new QHBoxLayout;
    body->setContentsMargins(0, 0, 0, 0);
    body->setSpacing(0);
    body->addWidget(m_nav);
    body->addWidget(m_pages, 1);

    auto* footer = new QHBoxLayout;
    footer->setContentsMargins(18, 10, 18, 14);
    auto* tip = subLabel(QStringLiteral("修改会立即生效并保存"));
    footer->addWidget(tip, 1);
    footer->addWidget(closeBtn);

    auto* root = new QVBoxLayout(this);
    root->setContentsMargins(0, 0, 0, 0);
    root->setSpacing(0);
    root->addLayout(body, 1);
    root->addLayout(footer);

    m_applyTimer = new QTimer(this);
    m_applyTimer->setSingleShot(true);
    m_applyTimer->setInterval(180);
    connect(m_applyTimer, &QTimer::timeout, this, &SettingsDialog::applyNow);

    m_loading = false;
}

// ---------------------------------------------------------------- 截图页
QWidget* SettingsDialog::makeShotPage() {
    QFormLayout* form = nullptr;
    QWidget* page = pageWrap(this, QStringLiteral("截图"),
                             QStringLiteral("决定截图如何触发、保存到哪里。"), form);

    m_hotkey = new QKeySequenceEdit(this);
    m_hotkey->setKeySequence(QKeySequence(Config::get().hotkeyText()));
    m_hotkey->setMaximumSequenceLength(1);
    form->addRow(QStringLiteral("全局热键"), m_hotkey);
    connect(m_hotkey, &QKeySequenceEdit::editingFinished, this, [this]() { scheduleApply(); });

    m_dir = new QLineEdit(Config::get().saveDir, this);
    auto* browse = new QPushButton(QStringLiteral("浏览…"), this);
    auto* dirRow = new QHBoxLayout;
    dirRow->addWidget(m_dir, 1);
    dirRow->addWidget(browse);
    form->addRow(QStringLiteral("保存目录"), dirRow);
    connect(m_dir, &QLineEdit::textEdited, this, [this]() { scheduleApply(); });
    connect(browse, &QPushButton::clicked, this, [this]() {
        QString d = QFileDialog::getExistingDirectory(this, QStringLiteral("选择保存目录"), m_dir->text());
        if (!d.isEmpty()) { m_dir->setText(d); scheduleApply(); }
    });

    m_fmt = new QComboBox(this);
    m_fmt->addItems({"png", "jpg", "webp", "bmp"});
    m_fmt->setCurrentText(Config::get().format);
    form->addRow(QStringLiteral("图片格式"), m_fmt);
    connect(m_fmt, &QComboBox::currentTextChanged, this, [this]() { scheduleApply(); });

    m_copy = new QCheckBox(QStringLiteral("截图后自动复制到剪贴板"), this);
    m_copy->setChecked(Config::get().copyAfterCapture);
    form->addRow(QString(), m_copy);
    connect(m_copy, &QCheckBox::toggled, this, [this]() { scheduleApply(); });

    m_magnifier = new QCheckBox(QStringLiteral("框选时显示放大镜与取色"), this);
    m_magnifier->setChecked(Config::get().showCursorMagnifier);
    form->addRow(QString(), m_magnifier);
    connect(m_magnifier, &QCheckBox::toggled, this, [this]() { scheduleApply(); });

    form->addRow(QString(), subLabel(QStringLiteral(
        "框选后可拖动手柄调整；Enter 复制，Ctrl+S 保存，Esc 取消。")));
    return page;
}

// ---------------------------------------------------------------- 识别页
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
        "离线时不会发起任何请求；首次在线识别会再确认一次。")));
    return page;
}

// ---------------------------------------------------------------- 录制页
QWidget* SettingsDialog::makeRecordPage() {
    QFormLayout* form = nullptr;
    QWidget* page = pageWrap(this, QStringLiteral("录制"),
                             QStringLiteral("录屏格式与音频来源。"), form);

    m_recFmt = new QComboBox(this);
    m_recFmt->addItem(QStringLiteral("MP4（H.264）"), QStringLiteral("mp4"));
    m_recFmt->addItem(QStringLiteral("GIF（无声）"), QStringLiteral("gif"));
    m_recFmt->setCurrentIndex(Config::get().recordFormat == "gif" ? 1 : 0);
    form->addRow(QStringLiteral("格式"), m_recFmt);
    connect(m_recFmt, &QComboBox::currentIndexChanged, this, [this]() { scheduleApply(); });

    m_recAudio = new QComboBox(this);
    m_recAudio->addItem(QStringLiteral("不录音"), QStringLiteral("none"));
    m_recAudio->addItem(QStringLiteral("系统声音"), QStringLiteral("system"));
    m_recAudio->addItem(QStringLiteral("麦克风"), QStringLiteral("mic"));
    m_recAudio->addItem(QStringLiteral("系统声音 + 麦克风"), QStringLiteral("both"));
    {
        int idx = m_recAudio->findData(Config::get().recordAudio);
        m_recAudio->setCurrentIndex(idx >= 0 ? idx : 0);
    }
    form->addRow(QStringLiteral("音频"), m_recAudio);
    connect(m_recAudio, &QComboBox::currentIndexChanged, this, [this]() { scheduleApply(); });

    form->addRow(QString(), subLabel(QStringLiteral(
        "音频按设备原生混音格式采集，不再经过系统低质量重采样；"
        "系统声与麦克风按平均值混合，避免削波。")));
    return page;
}

// ---------------------------------------------------------------- 翻译页
QWidget* SettingsDialog::makeTranslatePage() {
    QFormLayout* form = nullptr;
    QWidget* page = pageWrap(this, QStringLiteral("翻译"),
                             QStringLiteral("接入任意 OpenAI 兼容接口；不填 Key 则翻译不可用。"), form);

    m_trProvider = new QComboBox(this);
    for (const auto& p : TranslateClient::presets()) m_trProvider->addItem(p.name, p.id);
    {
        int idx = m_trProvider->findData(Config::get().translateProvider);
        m_trProvider->setCurrentIndex(idx >= 0 ? idx : 0);
    }
    form->addRow(QStringLiteral("引擎"), m_trProvider);

    m_trBase = new QLineEdit(Config::get().translateBaseUrl, this);
    m_trModel = new QLineEdit(Config::get().translateModel, this);
    m_trKey = new QLineEdit(this);
    m_trKey->setEchoMode(QLineEdit::Password);
    m_trKey->setPlaceholderText(QStringLiteral("留空则不启用翻译"));
    {
        QString cur = m_trProvider->currentData().toString();
        QString saved = secrets::load("translate_api_key_" + cur);
        if (saved.isEmpty()) saved = secrets::load("translate_api_key");
        if (!saved.isEmpty()) m_trKey->setText(saved);
    }
    m_trTarget = new QComboBox(this);
    m_trTarget->setEditable(true);
    m_trTarget->addItems({"简体中文", "繁體中文", "English", "日本語", "한국어",
                          "Français", "Deutsch", "Español", "Русский"});
    m_trTarget->setCurrentText(Config::get().translateTarget);

    m_trSource = new QComboBox(this);
    m_trSource->setEditable(true);
    m_trSource->addItems({"English", "自动检测", "简体中文", "繁體中文", "日本語", "한국어",
                          "Français", "Deutsch", "Español", "Русский"});
    m_trSource->setCurrentText(Config::get().translateSource);

    form->addRow(QStringLiteral("Base URL"), m_trBase);
    form->addRow(QStringLiteral("模型"), m_trModel);
    form->addRow(QStringLiteral("API Key"), m_trKey);
    form->addRow(QStringLiteral("源语言"), m_trSource);
    form->addRow(QStringLiteral("目标语言"), m_trTarget);

    auto applyPreset = [this](bool force) {
        QString id = m_trProvider->currentData().toString();
        ProviderPreset p = TranslateClient::presetById(id);
        if (force || m_trBase->text().isEmpty()) m_trBase->setText(p.baseUrl);
        if (force || m_trModel->text().isEmpty()) m_trModel->setText(p.model);
        QString k = secrets::load("translate_api_key_" + id);
        if (!k.isEmpty()) m_trKey->setText(k);
        scheduleApply();
    };
    connect(m_trProvider, &QComboBox::currentIndexChanged, this, [applyPreset](int) { applyPreset(true); });
    connect(m_trBase, &QLineEdit::textEdited, this, [this]() { scheduleApply(); });
    connect(m_trModel, &QLineEdit::textEdited, this, [this]() { scheduleApply(); });
    connect(m_trKey, &QLineEdit::textEdited, this, [this]() { scheduleApply(); });
    connect(m_trTarget, &QComboBox::currentTextChanged, this, [this]() { scheduleApply(); });
    connect(m_trSource, &QComboBox::currentTextChanged, this, [this]() { scheduleApply(); });

    m_trFallback = new QComboBox(this);
    m_trFallback->addItem(QStringLiteral("无（不降级）"), QString());
    for (const auto& p : TranslateClient::presets()) m_trFallback->addItem(p.name, p.id);
    {
        int idx = m_trFallback->findData(Config::get().translateFallbackProvider);
        m_trFallback->setCurrentIndex(idx >= 0 ? idx : 0);
    }
    form->addRow(QStringLiteral("备用引擎"), m_trFallback);
    connect(m_trFallback, &QComboBox::currentIndexChanged, this, [this]() { scheduleApply(); });

    m_trFallbackKey = new QLineEdit(this);
    m_trFallbackKey->setEchoMode(QLineEdit::Password);
    m_trFallbackKey->setPlaceholderText(QStringLiteral("备用引擎的 Key（可留空）"));
    {
        QString fid = Config::get().translateFallbackProvider;
        if (!fid.isEmpty()) m_trFallbackKey->setText(secrets::load("translate_api_key_" + fid));
    }
    form->addRow(QStringLiteral("备用 Key"), m_trFallbackKey);
    connect(m_trFallbackKey, &QLineEdit::textEdited, this, [this]() { scheduleApply(); });

    m_trGlossary = new QPlainTextEdit(this);
    m_trGlossary->setPlaceholderText(QStringLiteral("术语表，每行一条：原文=译法"));
    m_trGlossary->setPlainText(Config::get().translateGlossary);
    m_trGlossary->setFixedHeight(78);
    form->addRow(QStringLiteral("术语表"), m_trGlossary);
    connect(m_trGlossary, &QPlainTextEdit::textChanged, this, [this]() { scheduleApply(); });

    m_trChunk = new QSpinBox(this);
    m_trChunk->setRange(300, 8000);
    m_trChunk->setSingleStep(100);
    m_trChunk->setValue(Config::get().translateChunkChars);
    form->addRow(QStringLiteral("分段长度(字)"), m_trChunk);
    connect(m_trChunk, QOverload<int>::of(&QSpinBox::valueChanged), this, [this]() { scheduleApply(); });

    m_trStatus = new QLabel(this);
    m_trStatus->setObjectName(QStringLiteral("tsSub"));
    m_trStatus->setWordWrap(true);
    auto* testBtn = new QPushButton(QStringLiteral("测试连接"), this);
    auto* testRow = new QHBoxLayout;
    testRow->addWidget(testBtn);
    testRow->addWidget(m_trStatus, 1);
    form->addRow(QString(), testRow);

    connect(testBtn, &QPushButton::clicked, this, [this]() {
        applyNow();
        m_trStatus->setText(QStringLiteral("测试中…"));
        QApplication::processEvents();
        ProviderPreset p;
        p.id = m_trProvider->currentData().toString();
        p.baseUrl = m_trBase->text().trimmed();
        p.model = m_trModel->text().trimmed();
        TranslateClient client;
        auto r = client.testConnection(p, m_trKey->text().trimmed());
        m_trStatus->setText(r.ok ? QStringLiteral("连接成功：%1").arg(r.text.left(40))
                                 : QStringLiteral("连接失败：%1").arg(r.error));
    });
    return page;
}

// ---------------------------------------------------------------- 外观与其他
QWidget* SettingsDialog::makeOtherPage() {
    QFormLayout* form = nullptr;
    QWidget* page = pageWrap(this, QStringLiteral("外观与其他"),
                             QStringLiteral("主题、开机启动与版本信息。"), form);

    m_appearance = new QComboBox(this);
    m_appearance->addItem(QStringLiteral("跟随系统"), QStringLiteral("system"));
    m_appearance->addItem(QStringLiteral("浅色"), QStringLiteral("light"));
    m_appearance->addItem(QStringLiteral("深色"), QStringLiteral("dark"));
    {
        int idx = m_appearance->findData(Config::get().appearance);
        m_appearance->setCurrentIndex(idx >= 0 ? idx : 0);
    }
    form->addRow(QStringLiteral("主题"), m_appearance);
    connect(m_appearance, &QComboBox::currentIndexChanged, this, [this]() {
        Theme::Mode m = Theme::System;
        QString id = m_appearance->currentData().toString();
        if (id == "light") m = Theme::Light;
        else if (id == "dark") m = Theme::Dark;
        Theme::setMode(m, true);
    });

    m_autostart = new QCheckBox(QStringLiteral("开机自动启动"), this);
    {
        QSettings run("HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                      QSettings::NativeFormat);
        m_autostart->setChecked(run.contains("TackShot"));
    }
    form->addRow(QString(), m_autostart);
    connect(m_autostart, &QCheckBox::toggled, this, [this]() { scheduleApply(); });

    form->addRow(QString(), subLabel(QStringLiteral(
        "TackShot %1\n贴图窗口：拖动移动，滚轮缩放，双击切换 1:1，Esc 关闭。")
        .arg(QString::fromUtf8(APP_VERSION))));
    form->addRow(QString(), subLabel(QStringLiteral(
        "配置与缓存位置：%1").arg(Config::get().dataDir())));
    return page;
}

// ---------------------------------------------------------------- 立即生效
void SettingsDialog::scheduleApply() {
    if (m_loading || !m_applyTimer) return;
    m_applyTimer->start();
}

void SettingsDialog::applyNow() {
    if (m_loading) return;
    Config& c = Config::get();

    QKeySequence seq = m_hotkey ? m_hotkey->keySequence() : QKeySequence();
    if (!seq.isEmpty()) c.setHotkeyFromSequence(seq);
    if (m_dir) c.saveDir = m_dir->text();
    if (m_fmt) c.format = m_fmt->currentText();
    if (m_recFmt) c.recordFormat = m_recFmt->currentData().toString();
    if (m_recAudio) c.recordAudio = m_recAudio->currentData().toString();

    if (m_trProvider) c.translateProvider = m_trProvider->currentData().toString();
    if (m_trBase) c.translateBaseUrl = m_trBase->text().trimmed();
    if (m_trModel) c.translateModel = m_trModel->text().trimmed();
    if (m_trSource) c.translateSource = m_trSource->currentText().trimmed();
    if (m_trTarget) c.translateTarget = m_trTarget->currentText().trimmed();
    if (m_trKey) {
        QString key = m_trKey->text().trimmed();
        if (!key.isEmpty()) secrets::save("translate_api_key_" + c.translateProvider, key);
    }
    if (m_trFallback) c.translateFallbackProvider = m_trFallback->currentData().toString();
    if (m_trGlossary) c.translateGlossary = m_trGlossary->toPlainText();
    if (m_trChunk) c.translateChunkChars = m_trChunk->value();
    if (m_trFallbackKey && !c.translateFallbackProvider.isEmpty()) {
        QString fk = m_trFallbackKey->text().trimmed();
        if (!fk.isEmpty()) secrets::save("translate_api_key_" + c.translateFallbackProvider, fk);
    }

    if (m_ocrBackend) c.ocrBackend = m_ocrBackend->currentData().toString();
    if (m_ocrFormula) c.ocrFormula = m_ocrFormula->isChecked();
    if (m_visionProvider) c.visionProvider = m_visionProvider->currentData().toString();
    if (m_visionBase) c.visionBaseUrl = m_visionBase->text().trimmed();
    if (m_visionModel) c.visionModel = m_visionModel->text().trimmed();
    if (m_visionKey) {
        QString vk = m_visionKey->text().trimmed();
        if (!vk.isEmpty()) secrets::save("vision_api_key_" + c.visionProvider, vk);
    }

    if (m_copy) c.copyAfterCapture = m_copy->isChecked();
    if (m_magnifier) c.showCursorMagnifier = m_magnifier->isChecked();

    QSettings run("HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                  QSettings::NativeFormat);
    if (m_autostart) {
        if (m_autostart->isChecked())
            run.setValue("TackShot", "\"" + QCoreApplication::applicationFilePath().replace('/', '\\') + "\"");
        else
            run.remove("TackShot");
    }

    c.save();
    emit c.changed();
}

void SettingsDialog::accept() {
    applyNow();
    QDialog::accept();
}

void SettingsDialog::retranslatePlaceholders() {}
