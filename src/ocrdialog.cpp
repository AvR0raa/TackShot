#include "ocrdialog.h"
#include "theme.h"

#include <QClipboard>
#include <QComboBox>
#include <QFont>
#include <QFontDatabase>
#include <QFontMetrics>
#include <QGuiApplication>
#include <QHBoxLayout>
#include <QLabel>
#include <QMouseEvent>
#include <QPainter>
#include <QPalette>
#include <QPlainTextEdit>
#include <QPushButton>
#include <QShowEvent>
#include <QSignalBlocker>
#include <QSplitter>
#include <QTabWidget>
#include <QTextBlock>
#include <QTextCursor>
#include <QTextDocument>
#include <QVBoxLayout>
#include <QWidget>

#include <functional>
#include <utility>

namespace {

// 调色板里没有橙色；按需求，选中行高亮固定为橙色（深浅主题下都醒目）
const QColor kSelectOrange(0xff, 0x9f, 0x43);

// Palette 颜色 -> QSS 里的 rgba() 字符串
QString cssColor(const QColor& color, int alpha = -1) {
    QColor c = color;
    if (alpha >= 0) c.setAlpha(alpha);
    return QStringLiteral("rgba(%1,%2,%3,%4)")
        .arg(c.red()).arg(c.green()).arg(c.blue())
        .arg(c.alphaF(), 0, 'f', 3);
}

QColor withAlpha(const QColor& color, int alpha) {
    QColor c = color;
    c.setAlpha(alpha);
    return c;
}

} // namespace

// ---------------------------------------------------------------- 顶栏徽标
class OcrBadge : public QWidget {
public:
    explicit OcrBadge(bool accent, QWidget* parent = nullptr)
        : QWidget(parent), m_accent(accent) {
        QFont f = font();
        f.setPixelSize(12);
        setFont(f);
        setFixedHeight(22);
        setSizePolicy(QSizePolicy::Fixed, QSizePolicy::Fixed);
    }

    void setText(const QString& text) {
        if (m_text == text) return;
        m_text = text;
        setVisible(!m_text.isEmpty());
        updateGeometry();
        update();
    }

    QSize sizeHint() const override {
        const QFontMetrics fm(font());
        return QSize(fm.horizontalAdvance(m_text) + 20, 22);
    }

protected:
    void paintEvent(QPaintEvent*) override {
        if (m_text.isEmpty()) return;
        const Palette& c = Theme::p();
        QPainter p(this);
        p.setRenderHint(QPainter::Antialiasing, true);

        const QRectF r = QRectF(rect()).adjusted(0.5, 0.5, -0.5, -0.5);
        const QColor bg = m_accent ? c.accent : c.surfaceAlt;
        const QColor bd = m_accent ? c.accent : c.border;
        const QColor fg = m_accent ? c.accentText : c.subText;

        p.setPen(QPen(bd, 1));
        p.setBrush(bg);
        p.drawRoundedRect(r, r.height() / 2.0, r.height() / 2.0);
        p.setPen(fg);
        p.drawText(rect(), Qt::AlignCenter, m_text);
    }

private:
    QString m_text;
    bool    m_accent = false;
};

// ---------------------------------------------------------------- 左侧预览
class OcrPreview : public QWidget {
public:
    using Picker = std::function<void(int)>;

    explicit OcrPreview(QWidget* parent = nullptr) : QWidget(parent) {
        setObjectName(QStringLiteral("ocrPreview"));
        setMouseTracking(true);
        setMinimumSize(200, 180);
    }

    void setImage(const QImage& img) {
        m_img = img;
        update();
    }

    void setLines(const QVector<OcrLine>& lines) {
        m_lines = lines;
        update();
    }

    void setCurrent(int index) {
        if (m_current == index) return;
        m_current = index;
        update();
    }

    void setPicker(Picker fn) { m_pick = std::move(fn); }

protected:
    void paintEvent(QPaintEvent*) override {
        const Palette& c = Theme::p();
        QPainter p(this);
        p.setRenderHint(QPainter::Antialiasing, true);
        p.setRenderHint(QPainter::SmoothPixmapTransform, true);

        // 面板底
        const QRectF panel = QRectF(rect()).adjusted(0.5, 0.5, -0.5, -0.5);
        p.setPen(QPen(c.border, 1));
        p.setBrush(c.surfaceAlt);
        p.drawRoundedRect(panel, 8, 8);

        if (m_img.isNull()) {
            p.setPen(c.subText);
            p.drawText(rect(), Qt::AlignCenter, QStringLiteral("没有可显示的原图"));
            return;
        }

        // 缩略图（保持比例居中）
        const QRect dst = imageRect();
        p.setPen(Qt::NoPen);
        p.setBrush(c.surface);
        p.drawRect(dst);
        p.drawImage(dst, m_img);

        p.setBrush(Qt::NoBrush);
        p.setPen(QPen(c.border, 1));
        p.drawRect(QRectF(dst).adjusted(-0.5, -0.5, 0.5, 0.5));

        // 识别框：普通蓝色半透明；悬停加深；选中橙色
        for (int i = 0; i < m_lines.size(); ++i) {
            const QRectF r = mapBox(m_lines[i].box).adjusted(0.5, 0.5, -0.5, -0.5);
            if (r.width() < 1.0 || r.height() < 1.0) continue;

            const bool selected = (i == m_current);
            const bool hovered = (i == m_hover);
            QColor fill = c.accent;
            QColor edge = c.accent;
            qreal penWidth = 1.0;
            if (selected) {
                fill = withAlpha(kSelectOrange, 64);
                edge = kSelectOrange;
                penWidth = 2.0;
            } else {
                fill.setAlpha(hovered ? 78 : 46);
                edge.setAlpha(hovered ? 230 : 180);
                penWidth = hovered ? 1.6 : 1.0;
            }
            p.setBrush(fill);
            p.setPen(QPen(edge, penWidth));
            p.drawRect(r);
        }
    }

    void mousePressEvent(QMouseEvent* e) override {
        if (e->button() != Qt::LeftButton) {
            QWidget::mousePressEvent(e);
            return;
        }
        const int hit = hitTest(e->position().toPoint());
        if (hit >= 0) {
            setCurrent(hit);
            if (m_pick) m_pick(hit);
        }
        e->accept();
    }

    void mouseMoveEvent(QMouseEvent* e) override {
        const int hit = hitTest(e->position().toPoint());
        if (hit != m_hover) {
            m_hover = hit;
            setCursor(hit >= 0 ? Qt::PointingHandCursor : Qt::ArrowCursor);
            update();
        }
        QWidget::mouseMoveEvent(e);
    }

    void leaveEvent(QEvent* e) override {
        if (m_hover != -1) {
            m_hover = -1;
            update();
        }
        QWidget::leaveEvent(e);
    }

private:
    QRect imageRect() const {
        if (m_img.isNull()) return QRect();
        const int pad = 12;
        const QSize avail(qMax(1, width() - pad * 2), qMax(1, height() - pad * 2));
        const QSize dst = m_img.size().scaled(avail, Qt::KeepAspectRatio);
        return QRect(QPoint((width() - dst.width()) / 2, (height() - dst.height()) / 2), dst);
    }

    QRectF mapBox(const QRect& box) const {
        const QRect dst = imageRect();
        if (dst.isEmpty() || m_img.width() <= 0 || m_img.height() <= 0) return QRectF();
        const qreal sx = qreal(dst.width()) / qreal(m_img.width());
        const qreal sy = qreal(dst.height()) / qreal(m_img.height());
        return QRectF(dst.left() + box.x() * sx, dst.top() + box.y() * sy,
                      box.width() * sx, box.height() * sy);
    }

    int hitTest(const QPoint& pos) const {
        for (int i = m_lines.size() - 1; i >= 0; --i) {
            if (mapBox(m_lines[i].box).adjusted(-1, -1, 1, 1).contains(pos)) return i;
        }
        return -1;
    }

    QImage           m_img;
    QVector<OcrLine> m_lines;
    int              m_current = -1;
    int              m_hover = -1;
    Picker           m_pick;
};

// ---------------------------------------------------------------- 对话框
OcrDialog::OcrDialog(const OcrDialogInput& in, QWidget* parent)
    : QDialog(parent), m_in(in), m_lines(in.lines) {
    setWindowTitle(QStringLiteral("识别结果"));
    setWindowFlag(Qt::FramelessWindowHint, false);  // 普通有边框对话框
    resize(900, 600);
    setMinimumSize(760, 480);

    buildUi();
    applyTheme();
    connect(&Theme::instance(), &Theme::changed, this, [this]() { applyTheme(); });

    // 默认高亮第一行，与文字页光标保持一致
    if (!m_lines.isEmpty()) {
        m_currentLine = 0;
        if (m_preview) m_preview->setCurrent(0);
    }
    updateBadges();
    updateButtons();
}

void OcrDialog::buildUi() {
    m_header = makeHeader();
    QWidget* body = makeBody();
    m_footer = makeFooter();

    auto* root = new QVBoxLayout(this);
    root->setContentsMargins(0, 0, 0, 0);
    root->setSpacing(0);
    root->addWidget(m_header);
    root->addWidget(body, 1);
    root->addWidget(m_footer);
}

QWidget* OcrDialog::makeHeader() {
    auto* bar = new QWidget(this);
    bar->setObjectName(QStringLiteral("ocrHeader"));
    auto* lay = new QHBoxLayout(bar);
    lay->setContentsMargins(16, 10, 12, 10);
    lay->setSpacing(8);

    auto* title = new QLabel(QStringLiteral("识别结果"), bar);
    QFont f = title->font();
    f.setPixelSize(15);
    f.setBold(true);
    title->setFont(f);
    lay->addWidget(title);
    lay->addSpacing(2);

    m_backendBadge = new OcrBadge(true, bar);
    m_linesBadge = new OcrBadge(false, bar);
    m_timeBadge = new OcrBadge(false, bar);
    lay->addWidget(m_backendBadge);
    lay->addWidget(m_linesBadge);
    lay->addWidget(m_timeBadge);
    lay->addStretch(1);

    auto* closeBtn = new QPushButton(QStringLiteral("关闭"), bar);
    closeBtn->setCursor(Qt::PointingHandCursor);
    connect(closeBtn, &QPushButton::clicked, this, &QDialog::close);
    lay->addWidget(closeBtn);
    return bar;
}

QWidget* OcrDialog::makeBody() {
    auto* host = new QWidget(this);
    auto* lay = new QVBoxLayout(host);
    lay->setContentsMargins(12, 10, 12, 8);
    lay->setSpacing(0);

    m_split = new QSplitter(Qt::Horizontal, host);
    m_split->setChildrenCollapsible(false);
    m_split->setHandleWidth(10);

    // 左：原图 + 识别框
    m_preview = new OcrPreview(m_split);
    m_preview->setImage(m_in.image);
    m_preview->setLines(m_lines);
    m_preview->setPicker([this](int index) {
        if (!m_text || !m_tabs || index < 0 ||
            index >= m_text->document()->blockCount()) return;
        m_tabs->setCurrentIndex(0);
        QTextCursor cur(m_text->document()->findBlockByNumber(index));
        m_text->setTextCursor(cur);
        m_text->setFocus();
        setCurrentLine(index);
    });

    // 右：文字 / 译文 / LaTeX
    m_tabs = new QTabWidget(m_split);
    m_tabs->setDocumentMode(true);
    m_tabs->addTab(makeTextPage(), QStringLiteral("文字"));
    m_tabs->addTab(makeTranslatedPage(), QStringLiteral("译文"));
    m_tabs->addTab(makeLatexPage(), QStringLiteral("LaTeX"));

    m_split->addWidget(m_preview);
    m_split->addWidget(m_tabs);
    m_split->setStretchFactor(0, 0);
    m_split->setStretchFactor(1, 1);
    m_split->setSizes({300, 600});

    lay->addWidget(m_split, 1);
    return host;
}

QWidget* OcrDialog::makeTextPage() {
    auto* page = new QWidget(m_tabs);
    auto* lay = new QVBoxLayout(page);
    lay->setContentsMargins(8, 8, 8, 8);
    lay->setSpacing(0);

    m_text = new QPlainTextEdit(page);
    m_text->setObjectName(QStringLiteral("ocrSourceText"));
    m_text->setLineWrapMode(QPlainTextEdit::NoWrap);
    m_text->setTabChangesFocus(true);
    m_text->setPlaceholderText(QStringLiteral("未识别到文字"));

    QStringList lines;
    lines.reserve(m_lines.size());
    for (const OcrLine& line : m_lines) lines << line.text;
    m_text->setPlainText(lines.join(QLatin1Char('\n')));
    m_text->moveCursor(QTextCursor::Start);

    // 文字页光标行 -> 左侧识别框高亮
    connect(m_text, &QPlainTextEdit::cursorPositionChanged, this, [this]() {
        if (!m_text) return;
        setCurrentLine(m_text->textCursor().blockNumber());
    });

    lay->addWidget(m_text);
    return page;
}

QWidget* OcrDialog::makeTranslatedPage() {
    auto* page = new QWidget(m_tabs);
    auto* lay = new QVBoxLayout(page);
    lay->setContentsMargins(8, 8, 8, 8);
    lay->setSpacing(0);

    m_translatedEdit = new QPlainTextEdit(page);
    m_translatedEdit->setObjectName(QStringLiteral("ocrTranslatedText"));
    m_translatedEdit->setReadOnly(true);
    m_translatedEdit->setLineWrapMode(QPlainTextEdit::NoWrap);
    m_translatedEdit->setPlaceholderText(QStringLiteral("点击下方『翻译』生成译文"));
    lay->addWidget(m_translatedEdit);
    return page;
}

QWidget* OcrDialog::makeLatexPage() {
    auto* page = new QWidget(m_tabs);
    auto* lay = new QVBoxLayout(page);
    lay->setContentsMargins(8, 8, 8, 8);
    lay->setSpacing(0);

    m_latexEdit = new QPlainTextEdit(page);
    m_latexEdit->setObjectName(QStringLiteral("ocrLatexText"));
    m_latexEdit->setReadOnly(true);
    m_latexEdit->setLineWrapMode(QPlainTextEdit::NoWrap);
    m_latexEdit->setFont(QFontDatabase::systemFont(QFontDatabase::FixedFont));
    m_latexEdit->setPlaceholderText(QStringLiteral("该图未检测到公式"));
    lay->addWidget(m_latexEdit);
    return page;
}

QWidget* OcrDialog::makeFooter() {
    auto* bar = new QWidget(this);
    bar->setObjectName(QStringLiteral("ocrFooter"));
    auto* lay = new QHBoxLayout(bar);
    lay->setContentsMargins(14, 9, 14, 11);
    lay->setSpacing(7);

    auto* srcLabel = new QLabel(QStringLiteral("源语言"), bar);
    srcLabel->setObjectName(QStringLiteral("tsSub"));
    lay->addWidget(srcLabel);

    m_srcLang = new QComboBox(bar);
    m_srcLang->setObjectName(QStringLiteral("ocrSourceLang"));
    m_srcLang->setMinimumWidth(96);
    fillLanguages(m_srcLang);
    m_srcLang->setCurrentText(QStringLiteral("English"));
    lay->addWidget(m_srcLang);

    auto* arrow = new QLabel(QStringLiteral("→"), bar);
    arrow->setObjectName(QStringLiteral("tsSub"));
    lay->addWidget(arrow);

    m_tgtLang = new QComboBox(bar);
    m_tgtLang->setObjectName(QStringLiteral("ocrTargetLang"));
    m_tgtLang->setMinimumWidth(96);
    fillLanguages(m_tgtLang);
    m_tgtLang->setCurrentText(QStringLiteral("简体中文"));
    lay->addWidget(m_tgtLang);

    auto* modelLabel = new QLabel(QStringLiteral("模型"), bar);
    modelLabel->setObjectName(QStringLiteral("tsSub"));
    lay->addWidget(modelLabel);

    m_model = new QComboBox(bar);
    m_model->setObjectName(QStringLiteral("ocrModel"));
    m_model->setMinimumWidth(120);
    m_model->setSizeAdjustPolicy(QComboBox::AdjustToContents);
    lay->addWidget(m_model);

    // 状态文字吃掉剩余空间并右对齐，不挤占底部按钮
    m_status = new QLabel(bar);
    m_status->setObjectName(QStringLiteral("tsSub"));
    m_status->setSizePolicy(QSizePolicy::Ignored, QSizePolicy::Preferred);
    m_status->setAlignment(Qt::AlignRight | Qt::AlignVCenter);
    lay->addWidget(m_status, 1);

    m_translateBtn = new QPushButton(QStringLiteral("翻译"), bar);
    m_translateBtn->setObjectName(QStringLiteral("tsPrimary"));
    m_translateBtn->setProperty("ocrAction", true);
    m_translateBtn->setCursor(Qt::PointingHandCursor);
    connect(m_translateBtn, &QPushButton::clicked, this, &OcrDialog::translateRequested);
    lay->addWidget(m_translateBtn);

    m_imageBtn = new QPushButton(QStringLiteral("译图"), bar);
    m_imageBtn->setProperty("ocrAction", true);
    m_imageBtn->setCursor(Qt::PointingHandCursor);
    connect(m_imageBtn, &QPushButton::clicked, this, &OcrDialog::imageTranslateRequested);
    lay->addWidget(m_imageBtn);

    m_copyBtn = new QPushButton(QStringLiteral("复制"), bar);
    m_copyBtn->setCursor(Qt::PointingHandCursor);
    m_copyBtn->setToolTip(QStringLiteral("复制当前标签页的文本"));
    connect(m_copyBtn, &QPushButton::clicked, this, &OcrDialog::copyCurrentPage);
    lay->addWidget(m_copyBtn);

    return bar;
}

// ---------------------------------------------------------------- 主题
void OcrDialog::applyTheme() {
    const Palette& c = Theme::p();

    if (m_header) {
        m_header->setStyleSheet(QStringLiteral(
            "QWidget#ocrHeader { background: %1; border-bottom: 1px solid %2; }")
            .arg(cssColor(c.surface), cssColor(c.border)));
    }
    if (m_footer) {
        // 全局样式表没有 :disabled 规则，这里只为「翻译 / 译图」补一个灰态
        m_footer->setStyleSheet(QStringLiteral(
            "QWidget#ocrFooter { background: %1; border-top: 1px solid %2; }"
            "QPushButton[ocrAction=\"true\"]:disabled { background: %3; color: %4;"
            "  border: 1px solid %5; }")
            .arg(cssColor(c.surface), cssColor(c.border), cssColor(c.surfaceAlt),
                 cssColor(c.subText), cssColor(c.border)));
    }
    if (m_tabs) {
        m_tabs->setStyleSheet(QStringLiteral(
            "QTabWidget::pane { border: 1px solid %1; border-radius: 8px;"
            "  background: %2; top: -1px; }"
            "QTabBar::tab { background: transparent; color: %3; border: 1px solid transparent;"
            "  border-top-left-radius: 6px; border-top-right-radius: 6px;"
            "  padding: 5px 16px; margin-right: 3px; }"
            "QTabBar::tab:hover { color: %4; }"
            "QTabBar::tab:selected { background: %2; color: %4;"
            "  border-color: %1; border-bottom-color: %2; }")
            .arg(cssColor(c.border), cssColor(c.surface),
                 cssColor(c.subText), cssColor(c.text)));
    }

    // 未翻译 / 无公式时的灰色提示
    auto setPlaceholderColor = [&c](QPlainTextEdit* edit) {
        if (!edit) return;
        QPalette pal = edit->palette();
        pal.setColor(QPalette::PlaceholderText, c.subText);
        edit->setPalette(pal);
    };
    setPlaceholderColor(m_text);
    setPlaceholderColor(m_translatedEdit);
    setPlaceholderColor(m_latexEdit);

    if (m_preview) m_preview->update();
    if (m_backendBadge) m_backendBadge->update();
    if (m_linesBadge) m_linesBadge->update();
    if (m_timeBadge) m_timeBadge->update();
}

void OcrDialog::updateBadges() {
    if (!m_backendBadge) return;

    const QString backend = m_in.backend.trimmed();
    m_backendBadge->setText(backend);
    m_backendBadge->setVisible(!backend.isEmpty());

    m_linesBadge->setText(QStringLiteral("%1 行").arg(m_lines.size()));

    if (m_in.elapsedMs > 0) {
        const QString elapsed = m_in.elapsedMs >= 1000
            ? QStringLiteral("%1 s").arg(m_in.elapsedMs / 1000.0, 0, 'f', 2)
            : QStringLiteral("%1 ms").arg(m_in.elapsedMs);
        m_timeBadge->setText(elapsed);
    } else {
        m_timeBadge->setText(QString());
    }
}

void OcrDialog::updateButtons() {
    if (!m_translateBtn || !m_imageBtn) return;

    const bool enabled = m_online && !m_busy;
    const QString waitTip = QStringLiteral("正在处理，请稍候");

    m_translateBtn->setEnabled(enabled);
    m_translateBtn->setToolTip(!m_online
        ? QStringLiteral("离线模式：未配置在线翻译服务")
        : (m_busy ? waitTip : QStringLiteral("把识别到的文字翻译成目标语言")));

    m_imageBtn->setEnabled(enabled);
    m_imageBtn->setToolTip(!m_online
        ? QStringLiteral("离线模式：未配置在线翻译服务")
        : (m_busy ? waitTip : QStringLiteral("在原图上叠加译文")));
}

// ---------------------------------------------------------------- 对外接口
void OcrDialog::setTranslated(const QStringList& translated) {
    if (!m_translatedEdit) return;
    m_translatedEdit->setPlainText(translated.join(QLatin1Char('\n')));
    if (translated.isEmpty()) return;
    if (m_tabs) m_tabs->setCurrentIndex(1);
}

void OcrDialog::setLatex(const QString& latex) {
    if (!m_latexEdit) return;
    m_latexEdit->setPlainText(latex);
    if (!latex.trimmed().isEmpty() && m_tabs) m_tabs->setCurrentIndex(2);
}

void OcrDialog::setBusy(bool busy, const QString& status) {
    m_busy = busy;
    updateButtons();
    if (!status.isEmpty()) setStatusText(status);
}

void OcrDialog::setStatusText(const QString& status) {
    if (!m_status) return;
    m_status->setText(status);
    m_status->setToolTip(status);
}

QStringList OcrDialog::sourceLines() const {
    QStringList out;
    if (!m_text) return out;
    const QStringList raw = m_text->toPlainText().split(QLatin1Char('\n'));
    out.reserve(raw.size());
    for (const QString& line : raw) {
        if (!line.trimmed().isEmpty()) out << line;
    }
    return out;
}

QVector<OcrLine> OcrDialog::lines() const {
    return m_lines;
}

QString OcrDialog::sourceLang() const {
    return m_srcLang ? m_srcLang->currentText() : QStringLiteral("English");
}

QString OcrDialog::targetLang() const {
    return m_tgtLang ? m_tgtLang->currentText() : QStringLiteral("简体中文");
}

QString OcrDialog::modelId() const {
    return m_model ? m_model->currentText().trimmed() : QString();
}

void OcrDialog::setSourceLang(const QString& lang) {
    selectLanguage(m_srcLang, lang);
}

void OcrDialog::setTargetLang(const QString& lang) {
    selectLanguage(m_tgtLang, lang);
}

void OcrDialog::setModels(const QStringList& ids, const QString& current) {
    if (!m_model) return;
    QSignalBlocker block(m_model);
    m_model->clear();
    m_model->addItems(ids);
    if (!current.isEmpty() && m_model->findText(current) < 0) m_model->addItem(current);
    if (!current.isEmpty()) m_model->setCurrentText(current);
    else if (m_model->count() > 0) m_model->setCurrentIndex(0);
    m_model->setEnabled(m_model->count() > 1);
}

void OcrDialog::setOnlineAvailable(bool available) {
    m_online = available;
    updateButtons();
}

// ---------------------------------------------------------------- 内部
void OcrDialog::setCurrentLine(int index) {
    if (index == m_currentLine) return;
    m_currentLine = index;
    if (m_preview) m_preview->setCurrent(index);
}

void OcrDialog::copyCurrentPage() {
    const QString text = currentPageText();
    if (text.isEmpty()) {
        setStatusText(QStringLiteral("当前页面没有可复制的文本"));
        return;
    }
    if (QClipboard* clipboard = QGuiApplication::clipboard()) clipboard->setText(text);
    setStatusText(QStringLiteral("已复制到剪贴板"));
    emit copyRequested(text);
}

QString OcrDialog::currentPageText() const {
    if (!m_tabs) return QString();
    switch (m_tabs->currentIndex()) {
    case 0: return m_text ? m_text->toPlainText() : QString();
    case 1: return m_translatedEdit ? m_translatedEdit->toPlainText() : QString();
    case 2: return m_latexEdit ? m_latexEdit->toPlainText() : QString();
    default: return QString();
    }
}

void OcrDialog::showEvent(QShowEvent* e) {
    QDialog::showEvent(e);
    if (m_shown) return;
    m_shown = true;
    if (m_text) m_text->setFocus();
}

void OcrDialog::fillLanguages(QComboBox* box) {
    if (!box) return;
    static const QStringList kLanguages = {
        QStringLiteral("English"),
        QStringLiteral("自动检测"),
        QStringLiteral("日本語"),
        QStringLiteral("한국어"),
        QStringLiteral("Français"),
        QStringLiteral("Deutsch"),
        QStringLiteral("Español"),
        QStringLiteral("Русский"),
        QStringLiteral("简体中文"),
        QStringLiteral("繁體中文")
    };
    box->addItems(kLanguages);
}

void OcrDialog::selectLanguage(QComboBox* box, const QString& lang) {
    if (!box || lang.isEmpty()) return;
    int index = box->findText(lang);
    if (index < 0) {
        box->addItem(lang);
        index = box->count() - 1;
    }
    box->setCurrentIndex(index);
}
