#include "overlay.h"
#include <QTabWidget>
#include "config.h"
#include "capture.h"
#include "theme.h"
#include "common.h"

#include <QPainter>
#include <QPainterPath>
#include <QMouseEvent>
#include <QKeyEvent>
#include <QApplication>
#include <QClipboard>
#include <QToolButton>
#include <QSpinBox>
#include <QHBoxLayout>
#include <QColorDialog>
#include <QDir>
#include <QDateTime>
#include <QStandardPaths>
#include <QFileInfo>
#include <QDebug>
#include <QImageWriter>
#include <QMessageBox>
#include <QInputDialog>
#include <QLineEdit>
#include <QPlainTextEdit>
#include <QLabel>
#include <QApplication>
#include <QDialogButtonBox>
#include <QPushButton>
#include <QVBoxLayout>
#include <QDialog>
#include "ocrline.h"
#include "ocrdialog.h"
#include "vision.h"
#include "baidu.h"
#include "simpletex.h"
#include "sessions.h"
#include "translate.h"
#include "secrets.h"
#include <QPropertyAnimation>
#include <QWindow>
#include <QTimer>
#include <QVariantAnimation>
#include <QGraphicsDropShadowEffect>
#include <QFrame>
#include <QScreen>
#include <QDateTime>
#include <QFile>
#include <QElapsedTimer>
#include <QApplication>
#include <QClipboard>
#include <QAbstractAnimation>
#include <QFileDialog>
#include <QFile>
#include <QElapsedTimer>
#include <QApplication>
#include <QClipboard>
#include <QDir>
#include <QIcon>
#include <QRegion>
#include <QtMath>
#include <QPixmap>

namespace {

QIcon makeIcon(Tool t, const QColor& c) {
    QIcon icon;
    for (int scale : {1, 2}) {
        QPixmap pm(20 * scale, 20 * scale);
        pm.fill(Qt::transparent);
        pm.setDevicePixelRatio(scale);
        QPainter p(&pm);
        p.setRenderHint(QPainter::Antialiasing, true);
        p.setPen(QPen(c, 1.7, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
        p.setBrush(Qt::NoBrush);
        switch (t) {
        case Tool::Rect:     p.drawRoundedRect(QRectF(3.5, 4.5, 13, 11), 1.5, 1.5); break;
        case Tool::Ellipse:  p.drawEllipse(QRectF(3.5, 4.5, 13, 11)); break;
        case Tool::Arrow:    p.drawLine(QPointF(4, 16), QPointF(15.5, 5.5));
                             p.drawLine(QPointF(15.5, 5.5), QPointF(10, 5.5));
                             p.drawLine(QPointF(15.5, 5.5), QPointF(15.5, 11)); break;
        case Tool::Line:     p.drawLine(QPointF(4, 16), QPointF(16, 4)); break;
        case Tool::Pen:      { QPainterPath path;
                               path.moveTo(4, 14.5);
                               path.cubicTo(7, 6, 10, 17, 16, 6);
                               p.drawPath(path); break; }
        case Tool::Highlight: { QPen hp(c, 4.5, Qt::SolidLine, Qt::RoundCap);
                                p.setPen(hp);
                                p.drawLine(QPointF(5, 15), QPointF(15, 7)); break; }
        case Tool::Mosaic:   for (int i = 0; i < 3; ++i) for (int j = 0; j < 3; ++j) {
                                 QColor cc = ((i + j) % 2) ? c : c.darker(160);
                                 p.fillRect(QRectF(4.5 + i * 4, 5.5 + j * 4, 3.2, 3.2), cc);
                             }
                             break;
        case Tool::Text:     { QFont f; f.setBold(true); f.setPixelSize(14); p.setFont(f);
                               p.drawText(QRectF(1, 1, 18, 18), Qt::AlignCenter, "T"); break; }
        case Tool::Number:   p.drawEllipse(QRectF(3.5, 3.5, 13, 13)); break;
        case Tool::Select: {
            QPolygonF arrow;
            arrow << QPointF(5.5, 3.5) << QPointF(5.5, 16) << QPointF(9, 12.4)
                  << QPointF(11.6, 17.5) << QPointF(14, 16.3) << QPointF(11.4, 11.4)
                  << QPointF(16.3, 10.6);
            p.setBrush(c);
            p.setPen(Qt::NoPen);
            p.drawPolygon(arrow);
            break;
        }
        default: break;
        }
        p.end();
        icon.addPixmap(pm);
    }
    return icon;
}

} // namespace

Overlay::Overlay(const QImage& shot, const QRect& physicalRect, qreal dpr, QWidget* parent)
    : QWidget(parent), m_shot(shot), m_physRect(physicalRect), m_scale(dpr) {
    setWindowFlags(Qt::FramelessWindowHint | Qt::WindowStaysOnTopHint | Qt::Tool);
    setAttribute(Qt::WA_DeleteOnClose);
    setMouseTracking(true);
    setCursor(Qt::CrossCursor);
    setFocusPolicy(Qt::StrongFocus);

    m_color = QColor(Config::get().penColor);
    m_width = Config::get().penWidth;

    QRect logical(QPoint(qRound(physicalRect.x() / dpr), qRound(physicalRect.y() / dpr)),
                  QSize(qRound(physicalRect.width() / dpr), qRound(physicalRect.height() / dpr)));
    setGeometry(logical);
    buildToolbar();

    // 淡入只做在“遮罩透明度”上：不动窗口 opacity，
    // 因为 setWindowOpacity 在部分机器上会让 surface 按 1.0 缩放创建（125% 屏只画 80%）。
    setWindowOpacity(1.0);
    m_fade = 0.0;
    {
        auto* anim = new QVariantAnimation(this);
        anim->setStartValue(0.0);
        anim->setEndValue(1.0);
        anim->setDuration(130);
        anim->setEasingCurve(QEasingCurve::OutCubic);
        connect(anim, &QVariantAnimation::valueChanged, this, [this](const QVariant& v) {
            m_fade = v.toReal();
            update();
        });
        anim->start(QAbstractAnimation::DeleteWhenStopped);
    }
}

Overlay::~Overlay() = default;

void Overlay::buildToolbar() {
    m_bar = new QWidget(this);
    m_bar->setObjectName(QStringLiteral("tsBar"));
    m_bar->setAttribute(Qt::WA_StyledBackground, true);
    {
        const Palette& t = Theme::p();
        auto rgba = [](const QColor& c) {
            return QString("rgba(%1,%2,%3,%4)").arg(c.red()).arg(c.green())
                .arg(c.blue()).arg(c.alphaF(), 0, 'f', 3);
        };
        m_bar->setStyleSheet(QString(
            "#tsBar { background: %1; border: 1px solid %2; border-radius: 10px; }"
            "#tsBar QToolButton { border: 0; background: transparent; border-radius: 8px; padding: 0; }"
            "#tsBar QToolButton:hover { background: %3; }"
            "#tsBar QToolButton:pressed { background: %4; }"
            "#tsBar QToolButton:checked { background: %5; }"
            "#tsBar QToolButton#tsClose:hover { background: %6; }"
            "#tsBar QToolButton#tsAction { color: %7; font-size: 12px; padding: 0 9px; }"
            "#tsBar QToolButton#tsAction:hover { background: %3; }"
            "#tsBar QLabel { color: %7; font-size: 12px; }")
            .arg(rgba(t.surface), rgba(t.border), rgba(t.hover), rgba(t.pressed),
                 rgba(t.accent), rgba(t.danger), rgba(t.text)));
    }

    auto* lay = new QHBoxLayout(m_bar);
    lay->setContentsMargins(8, 6, 8, 6);
    lay->setSpacing(3);

    auto addSep = [&]() {
        auto* line = new QFrame(m_bar);
        line->setFrameShape(QFrame::VLine);
        line->setStyleSheet("color: rgba(255,255,255,0.12);");
        line->setFixedHeight(20);
        lay->addSpacing(3);
        lay->addWidget(line);
        lay->addSpacing(3);
    };

    const QVector<Tool> tools = {Tool::Select, Tool::Rect, Tool::Ellipse, Tool::Arrow, Tool::Line,
                                 Tool::Pen, Tool::Highlight, Tool::Mosaic, Tool::Text, Tool::Number};
    const QStringList tips = {QStringLiteral("选择 / 移动标注"),
                              QStringLiteral("矩形"), QStringLiteral("椭圆"),
                              QStringLiteral("箭头"), QStringLiteral("直线"),
                              QStringLiteral("画笔"), QStringLiteral("荧光笔"),
                              QStringLiteral("马赛克"), QStringLiteral("文字"),
                              QStringLiteral("序号")};
    for (int i = 0; i < tools.size(); ++i) {
        Tool t = tools[i];
        auto* b = new QToolButton(m_bar);
        b->setIcon(makeIcon(t, Theme::p().text));
        b->setIconSize(QSize(20, 20));
        b->setFixedSize(32, 32);
        b->setCheckable(true);
        b->setAutoRaise(true);
        b->setCursor(Qt::PointingHandCursor);
        b->setToolTip(tips.value(i));
        connect(b, &QToolButton::clicked, this, [this, t]() { onToolClicked(t); });
        lay->addWidget(b);
        m_toolButtons.append(b);
    }

    addSep();

    // 颜色
    m_colorBtn = new QToolButton(m_bar);
    m_colorBtn->setFixedSize(28, 28);
    m_colorBtn->setToolTip(QStringLiteral("颜色"));
    m_colorBtn->setCursor(Qt::PointingHandCursor);
    connect(m_colorBtn, &QToolButton::clicked, this, &Overlay::onPickColor);
    lay->addWidget(m_colorBtn);

    // 粗细：− 数值 + 预览
    auto* minus = new QToolButton(m_bar);
    minus->setText(QStringLiteral("−"));
    minus->setFixedSize(24, 28);
    minus->setStyleSheet(QString("QToolButton { color:%1; font-size:15px; }").arg(Theme::p().text.name()));
    minus->setToolTip(QStringLiteral("变细"));
    connect(minus, &QToolButton::clicked, this, [this]() { setWidth(int(m_width) - 1); });
    lay->addWidget(minus);

    m_widthLabel = new QLabel(QString::number(int(m_width)), m_bar);
    m_widthLabel->setFixedWidth(16);
    m_widthLabel->setAlignment(Qt::AlignCenter);
    lay->addWidget(m_widthLabel);

    auto* plus = new QToolButton(m_bar);
    plus->setText(QStringLiteral("+"));
    plus->setFixedSize(24, 28);
    plus->setStyleSheet(QString("QToolButton { color:%1; font-size:15px; }").arg(Theme::p().text.name()));
    plus->setToolTip(QStringLiteral("变粗"));
    connect(plus, &QToolButton::clicked, this, [this]() { setWidth(int(m_width) + 1); });
    lay->addWidget(plus);

    m_widthPreview = new QLabel(m_bar);
    m_widthPreview->setFixedSize(34, 28);
    m_widthPreview->setToolTip(QStringLiteral("当前笔画粗细"));
    lay->addWidget(m_widthPreview);

    addSep();

    auto addAction = [&](const QString& text, const QString& tip, auto fn, const char* name = "tsAction") {
        auto* b = new QToolButton(m_bar);
        b->setObjectName(QString::fromLatin1(name));
        b->setText(text);
        b->setToolTip(tip);
        b->setAutoRaise(true);
        b->setCursor(Qt::PointingHandCursor);
        b->setFixedHeight(30);
        b->setMinimumWidth(46);
        connect(b, &QToolButton::clicked, this, fn);
        lay->addWidget(b);
        return b;
    };

    addAction(QStringLiteral("识别"), QStringLiteral("本地 OCR 文字识别"), [this]() { onOcr(); });
    addAction(QStringLiteral("长图"), QStringLiteral("长截图（滚动拼接）"), [this]() { onLongShot(); });
    addAction(QStringLiteral("录制"), QStringLiteral("录制 GIF / MP4"), [this]() { onRecord(); });
    addSep();
    addAction(QStringLiteral("撤销"), QStringLiteral("撤销 (Ctrl+Z)"), [this]() { onUndo(); });
    addAction(QStringLiteral("重做"), QStringLiteral("重做 (Ctrl+Shift+Z)"), [this]() { onRedo(); });
    addSep();
    addAction(QStringLiteral("复制"), QStringLiteral("复制到剪贴板 (Enter)"), [this]() { onCopy(); });
    addAction(QStringLiteral("保存"), QStringLiteral("保存到文件 (Ctrl+S)"), [this]() { onSave(); });
    addAction(QStringLiteral("贴图"), QStringLiteral("钉在屏幕上"), [this]() { onPin(); });
    addAction(QStringLiteral("关闭"), QStringLiteral("取消 (Esc)"), [this]() { onClose(); }, "tsClose");

    m_bar->hide();
    updateToolButtons();
    m_bar->adjustSize();
}

void Overlay::placeToolbar() {
    if (!m_bar) return;
    m_bar->adjustSize();
    QRect sel = selRectWidget();
    QSize s = m_bar->sizeHint();
    int x = sel.right() - s.width();
    int y = sel.bottom() + 10;
    if (y + s.height() > height() - 6) y = sel.top() - s.height() - 10;
    if (y < 6) y = qBound(6, sel.center().y() - s.height() / 2, qMax(6, height() - s.height() - 6));
    x = qBound(6, x, qMax(6, width() - s.width() - 6));
    m_bar->setGeometry(x, y, s.width(), s.height());
    m_bar->show();
    m_bar->raise();
}

void Overlay::setWidth(int w) {
    w = qBound(1, w, 24);
    m_width = w;
    Config::get().penWidth = w;
    if (m_widthLabel) m_widthLabel->setText(QString::number(w));
    if (m_widthPreview) {
        QPixmap pm(34, 28);
        pm.fill(Qt::transparent);
        QPainter pp(&pm);
        pp.setRenderHint(QPainter::Antialiasing, true);
        pp.setPen(QPen(m_color, w, Qt::SolidLine, Qt::RoundCap));
        pp.drawLine(QPointF(4, 14), QPointF(30, 14));
        pp.end();
        m_widthPreview->setPixmap(pm);
    }
    update();
}

void Overlay::updateToolButtons() {
    const QVector<Tool> order = {Tool::Select, Tool::Rect, Tool::Ellipse, Tool::Arrow, Tool::Line,
                                 Tool::Pen, Tool::Highlight, Tool::Mosaic, Tool::Text, Tool::Number};
    for (int i = 0; i < m_toolButtons.size() && i < order.size(); ++i)
        m_toolButtons[i]->setChecked(order[i] == m_tool);
    if (m_colorBtn) {
        QPixmap pm(52, 52);
        pm.fill(Qt::transparent);
        pm.setDevicePixelRatio(2);
        QPainter p(&pm);
        p.setRenderHint(QPainter::Antialiasing, true);
        p.setPen(QPen(Theme::p().border, 1));
        p.setBrush(m_color);
        p.drawRoundedRect(QRectF(2, 2, 22, 22), 5, 5);
        p.end();
        m_colorBtn->setIcon(QIcon(pm));
        m_colorBtn->setIconSize(QSize(24, 24));
    }
    setWidth(int(m_width));
}

QRectF Overlay::annotBounds(const Annotation& a) const {
    if (a.pts.isEmpty()) return QRectF();
    // 注意：QRectF(p,p) 是“空矩形”，united() 会忽略它，两个点的标注会算成 0 尺寸。
    // 这里直接按 min/max 求包围盒。
    qreal minX = a.pts.first().x(), maxX = minX;
    qreal minY = a.pts.first().y(), maxY = minY;
    for (const QPointF& p : a.pts) {
        minX = qMin(minX, p.x()); maxX = qMax(maxX, p.x());
        minY = qMin(minY, p.y()); maxY = qMax(maxY, p.y());
    }
    QRectF r(minX, minY, maxX - minX, maxY - minY);
    if (a.type == Tool::Text) {
        QFont f;
        f.setPixelSize(std::max(12, int(a.width * 6)));
        QFontMetricsF fm(f);
        QRectF br = fm.boundingRect(QRectF(0, 0, 4000, 4000), Qt::TextWordWrap, a.text);
        r.setSize(br.size() + QSizeF(16, 6));
    } else if (a.type == Tool::Number) {
        qreal rad = std::max(14, int(a.width * 7)) * 0.75;
        r = QRectF(a.pts.first().x() - rad, a.pts.first().y() - rad, rad * 2, rad * 2);
    }
    if (r.width() < 6) r.setWidth(6);
    if (r.height() < 6) r.setHeight(6);
    return r;
}

int Overlay::hitAnnot(const QPointF& local) const {
    for (int i = m_annots.size() - 1; i >= 0; --i) {
        if (annotBounds(m_annots[i]).adjusted(-4, -4, 4, 4).contains(local)) return i;
    }
    return -1;
}

QRect Overlay::selRectWidget() const {
    if (m_sel.isEmpty()) return QRect();
    QRectF r(m_sel.x() / m_scale, m_sel.y() / m_scale, m_sel.width() / m_scale, m_sel.height() / m_scale);
    return r.toRect();
}

QPoint Overlay::toImage(const QPoint& p) const {
    return QPoint(qRound(p.x() * m_scale), qRound(p.y() * m_scale));
}

QPointF Overlay::toLocal(const QPoint& p) const {
    QPoint ip = toImage(p);
    return QPointF(ip.x() - m_sel.x(), ip.y() - m_sel.y());
}

int Overlay::handleAt(const QPoint& pos) const {
    if (m_sel.isEmpty()) return -1;
    QRect r = selRectWidget();
    const int hs = 6;
    QPoint pts[8] = {r.topLeft(), QPoint(r.center().x(), r.top()), r.topRight(),
                     QPoint(r.right(), r.center().y()), r.bottomRight(),
                     QPoint(r.center().x(), r.bottom()), r.bottomLeft(),
                     QPoint(r.left(), r.center().y())};
    for (int i = 0; i < 8; ++i) {
        QRect h(pts[i].x() - hs, pts[i].y() - hs, hs * 2, hs * 2);
        if (h.contains(pos)) return i;
    }
    return -1;
}

QImage Overlay::selectionImage(bool withAnnotations) const {
    if (m_sel.isEmpty()) return QImage();
    QImage canvas = m_shot.copy(m_sel.intersected(m_shot.rect()));
    if (withAnnotations) annot::renderToImage(canvas, m_annots);
    return canvas;
}

QImage Overlay::renderFinal() const {
    return selectionImage(true);
}

void Overlay::showEvent(QShowEvent* e) {
    QWidget::showEvent(e);

    // 1) 把窗口明确绑到目标屏；如果创建时落在了别的屏，surface 的 DPR 会是错的，
    //    必须重建一次（否则 125% 屏上的窗口只会画出 80% 的内容）。
    if (m_targetScreen) {
        if (QWindow* h = windowHandle()) {
            if (h->screen() != m_targetScreen) {
                h->setScreen(m_targetScreen);
                if (!m_rebuilding) {
                    m_rebuilding = true;
                    QTimer::singleShot(0, this, [this]() {
                        m_rebuilding = false;
                        hide();
                        show();
                    });
                }
            }
        }
    }

    // 2) 用显示器物理矩形反推窗口应有的逻辑尺寸：
    //    即使 Qt 的 DPR 判断有偏差，也要保证窗口铺满整块屏。
    {
        qreal wd = (windowHandle() ? windowHandle()->devicePixelRatio() : m_scale);
        if (wd < 0.1) wd = m_scale > 0.1 ? m_scale : 1.0;
        QRect mon = capture::nativeMonitorRect(quintptr(winId()));
        // 只有“覆盖整块显示器”的情况才用显示器矩形校正：
        // 若抓到的区域比显示器小（例如输出带黑边、已裁掉），必须保持原尺寸，否则内容会被拉伸。
        const bool coversMonitor = mon.isValid() && mon.width() > 100 &&
                                   qAbs(mon.width() - m_physRect.width()) < 64 &&
                                   qAbs(mon.height() - m_physRect.height()) < 64;
        if (coversMonitor) {
            QRect want(QPoint(qRound(mon.x() / wd), qRound(mon.y() / wd)),
                       QSize(qRound(mon.width() / wd), qRound(mon.height() / wd)));
            if (geometry() != want) {
                setGeometry(want);
                updateToolButtons();
                if (m_bar && m_bar->isVisible()) placeToolbar();
                update();
            }
            if (width() > 0) m_scale = double(m_shot.width()) / width();
        }
    }

    if (m_targetScreen) {
        QFile lf(Config::get().dataDir() + "/capture.log");
        if (lf.open(QIODevice::Append)) {
            lf.write(QString("[%1] overlay win=%2,%3 %4x%5 scale=%6 winDpr=%7 screen=%8 screenDpr=%9 "
                             "QT_SCALE_FACTOR=%10 QT_ENABLE_HIGHDPI_SCALING=%11\n")
                         .arg(QDateTime::currentDateTime().toString("MM-dd HH:mm:ss"))
                         .arg(x()).arg(y()).arg(width()).arg(height())
                         .arg(m_scale)
                         .arg(windowHandle() ? windowHandle()->devicePixelRatio() : -1.0)
                         .arg(m_targetScreen->name())
                         .arg(m_targetScreen->devicePixelRatio())
                         .arg(qEnvironmentVariable("QT_SCALE_FACTOR", "-"))
                         .arg(qEnvironmentVariable("QT_ENABLE_HIGHDPI_SCALING", "-"))
                         .toUtf8());
            lf.close();
        }
    }
}

void Overlay::paintEvent(QPaintEvent*) {
    QPainter p(this);
    p.setRenderHint(QPainter::SmoothPixmapTransform, true);
    p.setRenderHint(QPainter::Antialiasing, true);

    p.drawImage(rect(), m_shot);

    if (m_sel.isEmpty()) {
        p.fillRect(rect(), QColor(0, 0, 0, int(110 * m_fade)));
    } else {
        QRect sel = selRectWidget();
        QRegion outside(rect());
        outside -= QRegion(sel);
        for (const QRect& r : outside)
            p.fillRect(r, QColor(0, 0, 0, 110));

        QImage canvas = selectionImage(false);
        if (!canvas.isNull()) {
            QImage tmp = canvas;
            annot::renderToImage(tmp, m_annots);
            if (m_drawing && m_current.type != Tool::None) {
                QVector<Annotation> preview = m_annots;
                preview.append(m_current);
                tmp = canvas;
                annot::renderToImage(tmp, preview);
            }
            p.drawImage(sel, tmp);
        }

        // 边框与手柄
        QPen border(QColor("#2f6fed"), 1);
        p.setPen(border);
        p.setBrush(Qt::NoBrush);
        p.drawRect(sel.adjusted(0, 0, -1, -1));

        if (m_phase == Editing) {
            const qreal hs = 4.5;
            const QPointF pts[8] = {QPointF(sel.topLeft()), QPointF(sel.center().x(), sel.top()),
                                    QPointF(sel.topRight()), QPointF(sel.right(), sel.center().y()),
                                    QPointF(sel.bottomRight()), QPointF(sel.center().x(), sel.bottom()),
                                    QPointF(sel.bottomLeft()), QPointF(sel.left(), sel.center().y())};
            p.setPen(QPen(QColor(0, 0, 0, 90), 1));
            for (int i = 0; i < 8; ++i)
                p.drawEllipse(pts[i], hs + 1, hs + 1);
            p.setPen(QPen(Qt::white, 1.4));
            p.setBrush(QColor("#2f6fed"));
            for (int i = 0; i < 8; ++i)
                p.drawEllipse(pts[i], hs, hs);
        }

        // 尺寸标签（圆角胶囊）
        QString sizeText = QStringLiteral("%1 × %2").arg(m_sel.width()).arg(m_sel.height());
        QFont f = font();
        f.setPixelSize(12);
        p.setFont(f);
        QFontMetrics fm(f);
        int tw = fm.horizontalAdvance(sizeText) + 18;
        QRectF tag(sel.left(), sel.top() - 28, tw, 22);
        if (tag.top() < 2) tag.moveTop(sel.top() + 6);
        p.setPen(QPen(QColor(255, 255, 255, 30), 1));
        p.setBrush(Theme::isDark() ? QColor(18, 20, 24, 235) : QColor(255, 255, 255, 240));
        p.drawRoundedRect(tag, 11, 11);
        p.setPen(Theme::p().text);
        p.drawText(tag, Qt::AlignCenter, sizeText);
    }

    // 选中标注的控制框
    if (m_selected >= 0 && m_selected < m_annots.size()) {
        QRectF b = annotBounds(m_annots[m_selected]);
        QRectF wb(b.x() / m_scale + selRectWidget().x(), b.y() / m_scale + selRectWidget().y(),
                  b.width() / m_scale, b.height() / m_scale);
        p.setPen(QPen(QColor("#00c8ff"), 1, Qt::DashLine));
        p.setBrush(Qt::NoBrush);
        p.drawRect(wb);
        p.setPen(QPen(Qt::white, 1));
        p.setBrush(QColor("#00c8ff"));
        const QPointF pts[8] = {wb.topLeft(), QPointF(wb.center().x(), wb.top()), wb.topRight(),
                                QPointF(wb.right(), wb.center().y()), wb.bottomRight(),
                                QPointF(wb.center().x(), wb.bottom()), wb.bottomLeft(),
                                QPointF(wb.left(), wb.center().y())};
        for (const QPointF& q : pts) p.drawRect(QRectF(q.x() - 4, q.y() - 4, 8, 8));
    }

    // 放大镜
    if (m_hasCursor && (m_phase == Selecting)) {
        const int R = 60, zoom = 6;
        QPoint c = m_cursor;
        QRectF srcRect(c.x() * m_scale - R / zoom, c.y() * m_scale - R / zoom,
                       R * 2 / zoom, R * 2 / zoom);
        QRect dst(c.x() + 24, c.y() + 24, R * 2, R * 2);
        if (dst.right() > width()) dst.moveLeft(c.x() - R * 2 - 24);
        if (dst.bottom() > height()) dst.moveTop(c.y() - R * 2 - 24);

        p.save();
        QPainterPath clip;
        clip.addEllipse(dst);
        p.setClipPath(clip);
        p.drawImage(dst, m_shot, srcRect.toRect());
        p.restore();
        p.setPen(QPen(QColor("#2f6fed"), 2));
        p.drawEllipse(dst);
        p.setPen(QPen(Qt::white, 1));
        p.drawLine(dst.center().x() - 10, dst.center().y(), dst.center().x() + 10, dst.center().y());
        p.drawLine(dst.center().x(), dst.center().y() - 10, dst.center().x(), dst.center().y() + 10);

        QPoint ip = toImage(c);
        if (m_shot.rect().contains(ip)) {
            QColor pc = m_shot.pixelColor(ip);
            QString hex = pc.name().toUpper();
            QRect lab(dst.left(), dst.bottom() + 4, dst.width(), 18);
            p.setPen(Qt::NoPen);
            p.setBrush(QColor(0, 0, 0, 170));
            p.drawRoundedRect(lab, 3, 3);
            p.setPen(QColor("#e8eaed"));
            p.drawText(lab, Qt::AlignCenter, hex);
        }
    }
}

void Overlay::mousePressEvent(QMouseEvent* e) {
    if (e->button() != Qt::LeftButton) {
        if (e->button() == Qt::RightButton) {
            if (m_phase == Editing) { m_phase = Selecting; m_bar->hide(); m_sel = QRect(); update(); }
            else onClose();
        }
        return;
    }
    setFocus();
    QPoint pos = e->pos();

    if (m_phase == Selecting) {
        m_drag = DragSelect;
        m_dragStart = pos;
        m_sel = QRect();
        update();
        return;
    }

    // 1) 已选标注的缩放手柄
    if (m_selected >= 0 && m_selected < m_annots.size()) {
        QRectF b = annotBounds(m_annots[m_selected]);
        QRect sel0 = selRectWidget();
        QRectF wb(b.x() / m_scale + sel0.x(), b.y() / m_scale + sel0.y(),
                  b.width() / m_scale, b.height() / m_scale);
        const QPointF hp[8] = {wb.topLeft(), QPointF(wb.center().x(), wb.top()), wb.topRight(),
                               QPointF(wb.right(), wb.center().y()), wb.bottomRight(),
                               QPointF(wb.center().x(), wb.bottom()), wb.bottomLeft(),
                               QPointF(wb.left(), wb.center().y())};
        for (int i = 0; i < 8; ++i) {
            if (QRectF(hp[i].x() - 6, hp[i].y() - 6, 12, 12).contains(QPointF(pos))) {
                m_drag = DragAnnotResize;
                m_annotHandle = i;
                m_annotStartBox = b;
                m_annotPtsStart = m_annots[m_selected].pts;
                m_dragStart = pos;
                return;
            }
        }
    }

    // 2) 点到已有标注：选中并拖动
    {
        QPointF local = toLocal(pos);
        int hit = hitAnnot(local);
        if (hit >= 0 && (m_tool == Tool::None || m_tool == Tool::Select || hit == m_selected)) {
            m_selected = hit;
            m_drag = DragAnnot;
            m_annotStartBox = annotBounds(m_annots[hit]);
            m_annotPtsStart = m_annots[hit].pts;
            m_dragStart = pos;
            m_lastDragPos = pos;
            setCursor(Qt::SizeAllCursor);
            update();
            return;
        }
        if (hit < 0 && (m_tool == Tool::None || m_tool == Tool::Select)) m_selected = -1;
    }

    int h = handleAt(pos);
    if (h >= 0) {
        m_drag = DragResize;
        m_resizeHandle = h;
        m_selStart = m_sel;
        m_dragStart = pos;
        m_dragStartF = e->position();
        return;
    }

    QRect sel = selRectWidget();
    if (!sel.contains(pos)) {
        m_drag = DragSelect;
        m_dragStart = pos;
        m_sel = QRect();
        m_bar->hide();
        m_phase = Selecting;
        update();
        return;
    }

    if (m_tool == Tool::None || m_tool == Tool::Select) {
        m_drag = DragMove;
        m_dragStart = pos;
        m_dragStartF = e->position();   // 必须记录浮点按下点，否则位移算错（选区会跳走）
        m_selStart = m_sel;
        return;
    }

    if (m_tool == Tool::Text) {
        bool ok = false;
        QString text = QInputDialog::getText(this, QStringLiteral("文字"), QStringLiteral("输入文字："),
                                             QLineEdit::Normal, QString(), &ok);
        if (!ok || text.isEmpty()) return;
        Annotation an;
        an.type = Tool::Text;
        an.color = m_color;
        an.width = m_width;
        an.text = text;
        an.pts << toLocal(pos);
        m_annots.append(an);
        pushHistory();
        update();
        return;
    }

    if (m_tool == Tool::Number) {
        Annotation an;
        an.type = Tool::Number;
        an.color = m_color;
        an.width = m_width;
        an.number = m_numberCounter++;
        an.pts << toLocal(pos);
        m_annots.append(an);
        pushHistory();
        update();
        return;
    }

    m_drag = DragDraw;
    m_drawing = true;
    m_current = Annotation();
    m_current.type = m_tool;
    m_current.color = m_color;
    m_current.width = m_width;
    QPointF local = toLocal(pos);
    m_current.pts << local << local;
}

void Overlay::mouseMoveEvent(QMouseEvent* e) {
    m_cursor = e->pos();
    m_hasCursor = true;

    if (m_phase == Selecting) {
        if (m_drag == DragSelect) {
            QRect r = QRect(m_dragStart, e->pos()).normalized();
            QRect bounds = rect();
            r = r.intersected(bounds);
            m_sel = QRect(toImage(r.topLeft()), QSize(qRound(r.width() * m_scale), qRound(r.height() * m_scale)));
            m_sel = m_sel.intersected(m_shot.rect());
        }
        update();
        return;
    }

    if (m_drag == DragAnnot && m_selected >= 0 && m_selected < m_annots.size()) {
        QPointF d((e->pos().x() - m_lastDragPos.x()) * m_scale,
                  (e->pos().y() - m_lastDragPos.y()) * m_scale);
        for (QPointF& pt : m_annots[m_selected].pts) pt += d;
        m_lastDragPos = e->pos();
        update();
        return;
    }
    if (m_drag == DragAnnotResize && m_selected >= 0 && m_selected < m_annots.size()) {
        QPointF cur = toLocal(e->pos());
        QRectF nb = m_annotStartBox;
        switch (m_annotHandle) {
        case 0: nb.setTopLeft(cur); break;
        case 1: nb.setTop(cur.y()); break;
        case 2: nb.setTopRight(cur); break;
        case 3: nb.setRight(cur.x()); break;
        case 4: nb.setBottomRight(cur); break;
        case 5: nb.setBottom(cur.y()); break;
        case 6: nb.setBottomLeft(cur); break;
        case 7: nb.setLeft(cur.x()); break;
        }
        nb = nb.normalized();
        if (nb.width() < 4) nb.setWidth(4);
        if (nb.height() < 4) nb.setHeight(4);
        const qreal sx = m_annotStartBox.width() > 0.1 ? nb.width() / m_annotStartBox.width() : 1.0;
        const qreal sy = m_annotStartBox.height() > 0.1 ? nb.height() / m_annotStartBox.height() : 1.0;
        QVector<QPointF> pts = m_annotPtsStart;
        for (QPointF& pt : pts) {
            pt = QPointF(nb.left() + (pt.x() - m_annotStartBox.left()) * sx,
                         nb.top() + (pt.y() - m_annotStartBox.top()) * sy);
        }
        m_annots[m_selected].pts = pts;
        update();
        return;
    }
    if (m_drag == DragMove) {
        // 用浮点位移、只取整一次：DPR=1.25 时逐帧取整会让选区来回抖 1px
        const QPointF d = (e->position() - m_dragStartF) * m_scale;
        QRect r = m_selStart.translated(qRound(d.x()), qRound(d.y()));
        QRect clamped = r.intersected(m_shot.rect());
        if (clamped.size() != m_selStart.size()) {
            // 碰到边界：保持尺寸，改为夹住位置
            clamped.moveLeft(qBound(0, r.left(), qMax(0, m_shot.width() - m_selStart.width())));
            clamped.moveTop(qBound(0, r.top(), qMax(0, m_shot.height() - m_selStart.height())));
            clamped.setSize(m_selStart.size());
        }
        if (clamped != m_sel) {
            m_sel = clamped;
            placeToolbar();
            update();
        }
        return;
    }
    if (m_drag == DragResize) {
        QRect r = m_selStart;
        const QPointF df = (e->position() - m_dragStartF) * m_scale;
        QPoint d(qRound(df.x()), qRound(df.y()));
        switch (m_resizeHandle) {
        case 0: r.setTopLeft(r.topLeft() + d); break;
        case 1: r.setTop(d.y() + r.top()); break;
        case 2: r.setTopRight(r.topRight() + d); break;
        case 3: r.setRight(r.right() + d.x()); break;
        case 4: r.setBottomRight(r.bottomRight() + d); break;
        case 5: r.setBottom(r.bottom() + d.y()); break;
        case 6: r.setBottomLeft(r.bottomLeft() + d); break;
        case 7: r.setLeft(r.left() + d.x()); break;
        }
        m_sel = r.normalized().intersected(m_shot.rect());
        placeToolbar();
        update();
        return;
    }
    if (m_drag == DragDraw && m_drawing) {
        QPointF local = toLocal(e->pos());
        if (m_current.type == Tool::Pen || m_current.type == Tool::Mosaic)
            m_current.pts.append(local);
        else if (m_current.pts.size() >= 2)
            m_current.pts[1] = local;
        else
            m_current.pts.append(local);
        update();
        return;
    }
    update();
}

void Overlay::mouseReleaseEvent(QMouseEvent* e) {
    if (e->button() != Qt::LeftButton) return;

    if (m_phase == Selecting && m_drag == DragSelect) {
        m_drag = DragNone;
        if (m_sel.width() > 3 && m_sel.height() > 3) finishSelection();
        else { m_sel = QRect(); update(); }
        return;
    }
    if (m_drag == DragAnnot || m_drag == DragAnnotResize) {
        m_drag = DragNone;
        m_annotHandle = -1;
        pushHistory();
        update();
        return;
    }
    if (m_drag == DragDraw) {
        m_drag = DragNone;
        m_drawing = false;
        if (m_current.pts.size() >= 2) {
            QRectF bb = QRectF(m_current.pts.first(), m_current.pts.last()).normalized();
            bool tiny = bb.width() < 2 && bb.height() < 2;
            if (!(tiny && m_current.type != Tool::Pen))
                m_annots.append(m_current);
        } else if (m_current.pts.size() == 1) {
            m_annots.append(m_current);
        }
        pushHistory();
        m_current = Annotation();
        update();
        return;
    }
    m_drag = DragNone;
    m_resizeHandle = -1;
}

void Overlay::demoSetup() {
    m_sel = QRect(180, 140, 1240, 720).intersected(m_shot.rect());
    m_phase = Editing;
    m_tool = Tool::Arrow;
    m_color = QColor("#ff3b30");
    m_width = 4;

    Annotation a;
    a.type = Tool::Rect;  a.color = QColor("#ff3b30"); a.width = 3;
    a.pts << QPointF(240, 230) << QPointF(760, 360);
    m_annots.append(a);

    a = Annotation();
    a.type = Tool::Ellipse; a.color = QColor("#ffcc00"); a.width = 4;
    a.pts << QPointF(820, 220) << QPointF(1180, 400);
    m_annots.append(a);

    a = Annotation();
    a.type = Tool::Arrow; a.color = QColor("#2f6fed"); a.width = 5;
    a.pts << QPointF(1260, 700) << QPointF(900, 470);
    m_annots.append(a);

    a = Annotation();
    a.type = Tool::Pen; a.color = QColor("#34c759"); a.width = 4;
    for (int i = 0; i < 40; ++i) {
        qreal x = 300 + i * 12;
        qreal y = 620 + qSin(i * 0.5) * 40;
        a.pts << QPointF(x, y);
    }
    m_annots.append(a);

    a = Annotation();
    a.type = Tool::Highlight; a.color = QColor("#ffcc00"); a.width = 4;
    a.pts << QPointF(260, 500) << QPointF(700, 520);
    m_annots.append(a);

    a = Annotation();
    a.type = Tool::Mosaic; a.color = QColor("#888888"); a.width = 6;
    a.pts << QPointF(900, 560) << QPointF(1180, 700);
    m_annots.append(a);

    a = Annotation();
    a.type = Tool::Text; a.color = QColor("#ffffff"); a.width = 4;
    a.text = QStringLiteral("TackShot 标注演示 123ABC");
    a.pts << QPointF(280, 700);
    m_annots.append(a);

    a = Annotation();
    a.type = Tool::Number; a.color = QColor("#ff3b30"); a.width = 4;
    a.number = 1;
    a.pts << QPointF(1240, 250);
    m_annots.append(a);

    a = Annotation();
    a.type = Tool::Number; a.color = QColor("#ff3b30"); a.width = 4;
    a.number = 2;
    a.pts << QPointF(820, 470);
    m_annots.append(a);

    // 标注点使用"相对选区"的本地坐标
    const QPointF off = m_sel.topLeft();
    for (Annotation& x : m_annots)
        for (QPointF& p : x.pts) p -= off;

    m_numberCounter = 3;
    updateToolButtons();
    placeToolbar();
    update();
}

void Overlay::demoSimPress(const QPoint& p) {
    QMouseEvent e(QEvent::MouseButtonPress, QPointF(p), mapToGlobal(QPointF(p)),
                  Qt::LeftButton, Qt::LeftButton, Qt::NoModifier);
    mousePressEvent(&e);
}
void Overlay::demoSimMove(const QPoint& p) {
    QMouseEvent e(QEvent::MouseMove, QPointF(p), mapToGlobal(QPointF(p)),
                  Qt::NoButton, Qt::LeftButton, Qt::NoModifier);
    mouseMoveEvent(&e);
}
void Overlay::demoSimRelease(const QPoint& p) {
    QMouseEvent e(QEvent::MouseButtonRelease, QPointF(p), mapToGlobal(QPointF(p)),
                  Qt::LeftButton, Qt::NoButton, Qt::NoModifier);
    mouseReleaseEvent(&e);
}

QVector<int> Overlay::demoUndoTest() {
    m_annots.clear();
    m_hist.clear();
    m_histPos = -1;
    pushHistory();
    QVector<int> out;
    for (int i = 0; i < 3; ++i) {
        Annotation a;
        a.type = Tool::Rect;
        a.color = Qt::red;
        a.width = 2;
        a.pts << QPointF(10 + i * 5, 10) << QPointF(60 + i * 5, 60);
        m_annots.append(a);
        pushHistory();
    }
    out << m_annots.size();
    onUndo(); out << m_annots.size();
    onUndo(); out << m_annots.size();
    onRedo(); out << m_annots.size();
    return out;
}

void Overlay::finishSelection() {
    m_phase = Editing;
    m_hist.clear();
    m_histPos = -1;
    pushHistory();
    m_tool = Tool::Rect;
    updateToolButtons();
    placeToolbar();
    update();
}

void Overlay::keyPressEvent(QKeyEvent* e) {
    if ((e->key() == Qt::Key_Delete || e->key() == Qt::Key_Backspace) &&
        m_selected >= 0 && m_selected < m_annots.size()) {
        m_annots.removeAt(m_selected);
        m_selected = -1;
        pushHistory();
        update();
        return;
    }
    if (e->key() == Qt::Key_Escape) {
        if (m_phase == Editing) {
            m_phase = Selecting; m_sel = QRect(); m_bar->hide(); m_annots.clear();
            m_numberCounter = 1; update();
        } else onClose();
        return;
    }
    if (e->key() == Qt::Key_Return || e->key() == Qt::Key_Enter) { onCopy(); return; }
    if (e->matches(QKeySequence::Copy)) { onCopy(); return; }
    if (e->matches(QKeySequence::Save)) { onSave(); return; }
    if (e->matches(QKeySequence::Undo)) { onUndo(); return; }
    if (e->matches(QKeySequence::Redo)) { onRedo(); return; }

    if (m_phase == Editing) {
        int dx = 0, dy = 0, step = (e->modifiers() & Qt::ShiftModifier) ? 10 : 1;
        switch (e->key()) {
        case Qt::Key_Left: dx = -step; break;
        case Qt::Key_Right: dx = step; break;
        case Qt::Key_Up: dy = -step; break;
        case Qt::Key_Down: dy = step; break;
        default: break;
        }
        if (dx || dy) {
            m_sel.translate(dx, dy);
            m_sel = m_sel.intersected(m_shot.rect());
            placeToolbar();
            update();
            return;
        }
    }
    QWidget::keyPressEvent(e);
}

void Overlay::onToolClicked(Tool t) {
    m_tool = (m_tool == t) ? Tool::None : t;
    updateToolButtons();
    setCursor(m_tool == Tool::None ? Qt::SizeAllCursor : Qt::CrossCursor);
}

void Overlay::onPickColor() {
    QColor c = QColorDialog::getColor(m_color, this, QStringLiteral("选择颜色"));
    if (!c.isValid()) return;
    m_color = c;
    Config::get().penColor = c.name();
    updateToolButtons();
}

void Overlay::pushHistory() {
    if (m_histPos + 1 < m_hist.size())
        m_hist.resize(m_histPos + 1);
    m_hist.append(m_annots);
    while (m_hist.size() > 60) m_hist.removeFirst();
    m_histPos = m_hist.size() - 1;
}

void Overlay::onUndo() {
    if (m_histPos <= 0) return;
    --m_histPos;
    m_annots = m_hist[m_histPos];
    update();
}

void Overlay::onRedo() {
    if (m_histPos + 1 >= m_hist.size()) return;
    ++m_histPos;
    m_annots = m_hist[m_histPos];
    update();
}

void Overlay::onCopy() {
    QImage img = renderFinal();
    if (img.isNull()) return;
    QApplication::clipboard()->setImage(img);
    if (Config::get().copyAfterCapture) {
        // 已复制
    }
    close();
    emit closed();
}

// 按选区尺寸把译文渲染回原图（图片翻译）
QImage Overlay::renderTranslated(const QImage& base, const QVector<OcrLine>& lines,
                                 const QStringList& translated) {
    QImage out = base.convertToFormat(QImage::Format_ARGB32);
    QPainter p(&out);
    p.setRenderHint(QPainter::TextAntialiasing, true);
    for (int i = 0; i < lines.size() && i < translated.size(); ++i) {
        if (translated[i].trimmed().isEmpty()) continue;
        const QRect box = lines[i].box;
        // 擦除区域比文本框略大，盖住原字的上下缘
        QRect erase(box.left() - 4, box.top() - int(box.height() * 0.22),
                    box.width() + 8, int(box.height() * 1.44));
        erase = erase.intersected(out.rect());
        if (erase.width() < 6 || erase.height() < 6) continue;

        // 背景色：从文本框外侧一圈取样（避开笔画）
        long long sr = 0, sg = 0, sb = 0; int n = 0;
        auto sample = [&](int x, int y) {
            if (x < 0 || y < 0 || x >= out.width() || y >= out.height()) return;
            QRgb c = out.pixel(x, y);
            sr += qRed(c); sg += qGreen(c); sb += qBlue(c); n++;
        };
        for (int x = box.left(); x <= box.right(); x += 3) {
            sample(x, box.top() - 4);
            sample(x, box.bottom() + 4);
        }
        QColor bg = n ? QColor(int(sr / n), int(sg / n), int(sb / n)) : QColor(Qt::white);
        QColor fg = (bg.lightnessF() > 0.55) ? QColor(25, 25, 25) : QColor(240, 240, 240);

        p.fillRect(erase, bg);

        QFont f(QStringLiteral("Microsoft YaHei"));
        int px = qMax(9, int(box.height() * 0.82));
        f.setPixelSize(px);
        QFontMetrics fm(f);
        const QString& text = translated[i];
        while (px > 8 && fm.horizontalAdvance(text) > erase.width()) {
            px -= 1;
            f.setPixelSize(px);
            fm = QFontMetrics(f);
        }
        p.setFont(f);
        p.setPen(fg);
        p.drawText(erase, Qt::AlignLeft | Qt::AlignVCenter, text);
    }
    p.end();
    return out;
}

// 中文语言名 -> 百度语言码
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

// 选区（图像坐标）-> 物理屏幕矩形
static QRect physRegionOf(const QRect& physBase, const QRect& sel) {
    return QRect(physBase.topLeft() + sel.topLeft(), sel.size());
}

void Overlay::onLongShot() {
    if (m_sel.isEmpty()) return;
    QRect region = physRegionOf(m_physRect, m_sel);
    hide();
    auto* bar = new LongShotBar(region);
    connect(bar, &LongShotBar::finished, this, [this](const QImage& img) {
        if (img.isNull()) return;
        QString dir = Config::get().saveDir;
        QDir().mkpath(dir);
        QString path = QString("%1/longshot_%2.png").arg(dir,
            QDateTime::currentDateTime().toString("yyyyMMdd_HHmmss"));
        img.save(path);
        QApplication::clipboard()->setImage(img);
        QMessageBox::information(nullptr, QStringLiteral("长截图"),
            QStringLiteral("已保存并复制到剪贴板：\n%1\n尺寸：%2 × %3")
                .arg(QDir::toNativeSeparators(path)).arg(img.width()).arg(img.height()));
        close();
        emit closed();
    });
    connect(bar, &LongShotBar::cancelled, this, [this]() { close(); emit closed(); });
    bar->show();
}

void Overlay::onRecord() {
    if (m_sel.isEmpty()) return;
    QRect region = physRegionOf(m_physRect, m_sel);
    hide();
    auto* bar = new RecordBar(region);
    connect(bar, &RecordBar::finished, this, [this](const QString& path) {
        QMessageBox::information(nullptr, QStringLiteral("录制完成"),
            QStringLiteral("已保存 GIF：\n%1").arg(QDir::toNativeSeparators(path)));
        close();
        emit closed();
    });
    connect(bar, &RecordBar::cancelled, this, [this]() { close(); emit closed(); });
    bar->show();
}

void Overlay::onSave() {
    QImage img = renderFinal();
    if (img.isNull()) return;
    QString dir = Config::get().saveDir;
    QDir().mkpath(dir);
    QString fmt = Config::get().format.toLower();
    if (fmt == "jpg" || fmt == "jpeg") fmt = "jpg";
    QString name = QDateTime::currentDateTime().toString("yyyyMMdd_HHmmss_zzz");
    QString path = QString("%1/%2.%3").arg(dir, name, fmt);
    int quality = 95;
    bool ok = img.save(path, nullptr, quality);
    if (ok && Config::get().copyAfterCapture)
        QApplication::clipboard()->setImage(img);
    Q_UNUSED(ok);
    close();
    emit closed();
}

void Overlay::onPin() {
    QImage img = renderFinal();
    if (img.isNull()) return;
    emit pinRequested(img);
    close();
    emit closed();
}

void Overlay::onClose() {
    close();
    emit closed();
}
