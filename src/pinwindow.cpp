#include "pinwindow.h"
#include "config.h"
#include "theme.h"

#include <QPainter>
#include <QPainterPath>
#include <QMouseEvent>
#include <QWheelEvent>
#include <QKeyEvent>
#include <QMenu>
#include <QKeySequence>
#include <QApplication>
#include <QClipboard>
#include <QDir>
#include <QDateTime>
#include <QContextMenuEvent>
#include <QGuiApplication>
#include <QScreen>
#include <QVariantAnimation>
#include <QTimer>

namespace {
constexpr int kBarH = 26;
constexpr int kBtnW = 26;
constexpr int kBtnCount = 4;
}

PinWindow::PinWindow(const QImage& img, QWidget* parent) : QWidget(parent), m_img(img) {
    setWindowFlags(Qt::FramelessWindowHint | Qt::WindowStaysOnTopHint | Qt::Tool);
    setAttribute(Qt::WA_DeleteOnClose);
    setMouseTracking(true);
    setWindowTitle(QStringLiteral("TackShot 贴图"));
    m_scaled = m_img;
    updateSize();

    // 入场：内容从 88% 放大到 100%，同时淡入（只作用于绘制，不动窗口 opacity）
    m_reveal = 0.0;
    auto* anim = new QVariantAnimation(this);
    anim->setStartValue(0.0);
    anim->setEndValue(1.0);
    anim->setDuration(150);
    anim->setEasingCurve(QEasingCurve::OutCubic);
    connect(anim, &QVariantAnimation::valueChanged, this, [this](const QVariant& v) {
        m_reveal = v.toReal();
        update();
    });
    anim->start(QAbstractAnimation::DeleteWhenStopped);

    // 兜底：若动画因任何原因没跑起来，200ms 后强制显示完
    QTimer::singleShot(200, this, [this]() {
        if (m_reveal < 1.0) { m_reveal = 1.0; update(); }
    });
}

void PinWindow::updateSize() {
    QSize s = QSize(qRound(m_img.width() * m_zoom), qRound(m_img.height() * m_zoom));
    if (s.width() < 24) s.setWidth(24);
    if (s.height() < 24) s.setHeight(24);
    m_scaled = m_img.scaled(s, Qt::IgnoreAspectRatio, Qt::SmoothTransformation);
    setFixedSize(s + QSize(0, 0));
}

void PinWindow::placeAt(const QPoint& globalPos) {
    QScreen* sc = QGuiApplication::screenAt(globalPos);
    if (!sc) sc = QGuiApplication::primaryScreen();
    QRect scr = sc ? sc->geometry() : QRect(0, 0, 1920, 1080);
    QPoint p = globalPos;
    if (p.x() + width() > scr.right()) p.setX(scr.right() - width());
    if (p.y() + height() > scr.bottom()) p.setY(scr.bottom() - height());
    if (p.x() < scr.left()) p.setX(scr.left());
    if (p.y() < scr.top()) p.setY(scr.top());
    move(p);
}

QRect PinWindow::barRect() const {
    return QRect(0, 0, width(), qMin(kBarH, height()));
}

QPointF PinWindow::buttonPos(int index) const {
    const qreal right = width() - 6 - index * (kBtnW + 2);
    return QPointF(right - kBtnW / 2.0, kBarH / 2.0);
}

int PinWindow::buttonAt(const QPoint& p) const {
    if (barRect().contains(p)) {
        for (int i = 0; i < kBtnCount; ++i) {
            const QPointF c = buttonPos(i);
            if (QRectF(c.x() - kBtnW / 2.0, c.y() - 9, kBtnW, 18).contains(QPointF(p)))
                return i;
        }
    }
    return -1;
}

void PinWindow::paintEvent(QPaintEvent*) {
    QPainter p(this);
    p.setRenderHint(QPainter::SmoothPixmapTransform, true);
    p.setRenderHint(QPainter::Antialiasing, true);

    // 入场缩放 + 淡入
    const qreal scale = 0.88 + 0.12 * m_reveal;
    p.setOpacity(qBound(0.0, m_reveal * 1.2, 1.0));
    if (scale < 0.999) {
        p.translate(width() / 2.0, height() / 2.0);
        p.scale(scale, scale);
        p.translate(-width() / 2.0, -height() / 2.0);
    }

    // 阴影（外扩渐变）
    const int sh = 10;
    for (int i = 0; i < sh; ++i) {
        QColor c = Theme::p().shadow;
        c.setAlpha(int(c.alpha() * (1.0 - double(i) / sh) * 0.35));
        p.setPen(QPen(c, 1));
        p.setBrush(Qt::NoBrush);
        p.drawRect(rect().adjusted(-i, -i, i, i));
    }

    p.drawImage(rect(), m_scaled);

    if (m_hover && m_reveal > 0.99) {
        // 顶部标题条
        QRect bar = barRect();
        QLinearGradient g(0, 0, 0, bar.height());
        g.setColorAt(0, QColor(0, 0, 0, 190));
        g.setColorAt(1, QColor(0, 0, 0, 90));
        p.setPen(Qt::NoPen);
        p.setBrush(g);
        p.drawRect(bar);

        // 左侧信息
        QFont f = font();
        f.setPixelSize(11);
        p.setFont(f);
        p.setPen(QColor(255, 255, 255, 225));
        const QString info = QStringLiteral("%1 × %2  ·  %3%")
                                 .arg(m_img.width()).arg(m_img.height())
                                 .arg(qRound(m_zoom * 100));
        p.drawText(bar.adjusted(8, 0, -kBtnCount * (kBtnW + 2) - 8, 0),
                   Qt::AlignLeft | Qt::AlignVCenter, info);

        // 右侧按钮：复制 / 保存 / 1:1 / 关闭
        static const char* glyphs[kBtnCount] = {"copy", "save", "1:1", "x"};
        for (int i = 0; i < kBtnCount; ++i) {
            const QPointF c = buttonPos(i);
            const QRectF hit(c.x() - kBtnW / 2.0, c.y() - 9, kBtnW, 18);
            const bool hot = (i == m_hoverBtn);
            if (i == kBtnCount - 1) {      // 关闭
                p.setBrush(hot ? QColor(255, 69, 58, 230) : QColor(255, 255, 255, 24));
            } else {
                p.setBrush(hot ? QColor(47, 111, 237, 230) : QColor(255, 255, 255, 24));
            }
            p.setPen(Qt::NoPen);
            p.drawRoundedRect(hit, 5, 5);

            p.setPen(QColor(255, 255, 255, 240));
            if (i == 2) {
                QFont bf = font();
                bf.setPixelSize(8);
                bf.setBold(true);
                p.setFont(bf);
                p.drawText(hit, Qt::AlignCenter, QStringLiteral("1:1"));
                p.setFont(f);
            } else if (i == 3) {
                QPen xp(QColor(255, 255, 255, 240), 1.6, Qt::SolidLine, Qt::RoundCap);
                p.setPen(xp);
                p.drawLine(QPointF(c.x() - 3.5, c.y() - 3.5), QPointF(c.x() + 3.5, c.y() + 3.5));
                p.drawLine(QPointF(c.x() - 3.5, c.y() + 3.5), QPointF(c.x() + 3.5, c.y() - 3.5));
            } else if (i == 0) {
                p.setBrush(Qt::NoBrush);
                p.setPen(QPen(QColor(255, 255, 255, 240), 1.4));
                p.drawRoundedRect(QRectF(c.x() - 5, c.y() - 4, 7, 8), 1.5, 1.5);
                p.drawRoundedRect(QRectF(c.x() - 2, c.y() - 6, 7, 8), 1.5, 1.5);
            } else {
                p.setBrush(Qt::NoBrush);
                p.setPen(QPen(QColor(255, 255, 255, 240), 1.4));
                p.drawLine(QPointF(c.x() - 4, c.y() - 5), QPointF(c.x() + 3, c.y() - 5));
                p.drawRoundedRect(QRectF(c.x() - 4, c.y() - 5, 7, 9), 1.5, 1.5);
            }
        }
    }
}

void PinWindow::mousePressEvent(QMouseEvent* e) {
    if (e->button() != Qt::LeftButton) return;
    const int btn = m_hover ? buttonAt(e->pos()) : -1;
    if (btn >= 0) {
        switch (btn) {
        case 0: copyImage(); break;
        case 1: saveToFile(); break;
        case 2: toggleOneToOne(); break;
        case 3: close(); break;
        }
        return;
    }
    m_dragging = true;
    m_dragBar = m_hover && barRect().contains(e->pos());
    m_dragOffset = e->globalPosition().toPoint() - frameGeometry().topLeft();
}

void PinWindow::mouseMoveEvent(QMouseEvent* e) {
    if (!m_hover) { m_hover = true; update(); }
    const int btn = buttonAt(e->pos());
    if (btn != m_hoverBtn) { m_hoverBtn = btn; update(); }
    if (m_dragging) move(e->globalPosition().toPoint() - m_dragOffset);
}

void PinWindow::mouseReleaseEvent(QMouseEvent*) {
    m_dragging = false;
    m_dragBar = false;
}

void PinWindow::leaveEvent(QEvent*) {
    m_hover = false;
    m_hoverBtn = -1;
    update();
}

void PinWindow::wheelEvent(QWheelEvent* e) {
    qreal factor = e->angleDelta().y() > 0 ? 1.1 : 1.0 / 1.1;
    qreal nz = qBound(0.1, m_zoom * factor, 8.0);
    if (qFuzzyCompare(nz, m_zoom)) return;
    m_zoom = nz;
    QPoint cur = mapToGlobal(e->position().toPoint());
    updateSize();
    move(cur - e->position().toPoint());
    update();
}

void PinWindow::mouseDoubleClickEvent(QMouseEvent*) {
    toggleOneToOne();
}

void PinWindow::toggleOneToOne() {
    const QPoint center = mapToGlobal(rect().center());
    m_zoom = qFuzzyCompare(m_zoom, 1.0) ? 2.0 : 1.0;
    updateSize();
    move(center - rect().center());
    update();
}

void PinWindow::copyImage() {
    QApplication::clipboard()->setImage(m_img);
}

void PinWindow::keyPressEvent(QKeyEvent* e) {
    if (e->key() == Qt::Key_Escape) { close(); return; }
    if (e->matches(QKeySequence::Copy)) { copyImage(); return; }
    if (e->matches(QKeySequence::Save)) { saveToFile(); return; }
    QWidget::keyPressEvent(e);
}

void PinWindow::contextMenuEvent(QContextMenuEvent* e) {
    QMenu m(this);
    m.addAction(QStringLiteral("复制图片"), this, [this]() { copyImage(); });
    m.addAction(QStringLiteral("另存为…"), this, [this]() { saveToFile(); });
    m.addSeparator();
    m.addAction(QStringLiteral("放大 10%"), this, [this]() {
        m_zoom = qBound(0.1, m_zoom * 1.1, 8.0); updateSize(); update();
    });
    m.addAction(QStringLiteral("缩小 10%"), this, [this]() {
        m_zoom = qBound(0.1, m_zoom / 1.1, 8.0); updateSize(); update();
    });
    m.addAction(QStringLiteral("原始大小 (1:1)"), this, [this]() {
        m_zoom = 1.0; updateSize(); update();
    });
    m.addSeparator();
    m.addAction(QStringLiteral("关闭"), this, [this]() { close(); });
    m.exec(e->globalPos());
}

void PinWindow::saveToFile() {
    QString dir = Config::get().saveDir;
    QDir().mkpath(dir);
    QString name = QDateTime::currentDateTime().toString("yyyyMMdd_HHmmss_zzz");
    QString path = QString("%1/%2.%3").arg(dir, name, Config::get().format);
    m_img.save(path);
}
