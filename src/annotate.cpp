#include "annotate.h"
#include <QPainterPath>
#include <QPolygonF>
#include <QFont>
#include <QFontMetrics>
#include <QtMath>
#include <algorithm>

namespace {

// 用二次贝塞尔平滑折线（走中点），消除锯齿棱角
QPainterPath smoothPath(const QVector<QPointF>& pts) {
    QPainterPath path;
    if (pts.isEmpty()) return path;
    path.moveTo(pts.first());
    if (pts.size() == 1) return path;
    if (pts.size() == 2) { path.lineTo(pts[1]); return path; }
    for (int i = 1; i < pts.size() - 1; ++i) {
        const QPointF mid = (pts[i] + pts[i + 1]) / 2.0;
        path.quadTo(pts[i], mid);
    }
    path.lineTo(pts.last());
    return path;
}

void pixelate(QImage& img, const QRect& rect, int cell) {
    if (cell < 2) cell = 2;
    QRect r = rect.intersected(img.rect());
    if (r.width() < cell || r.height() < cell) return;
    int sw = std::max(1, r.width() / cell);
    int sh = std::max(1, r.height() / cell);
    QImage small = img.copy(r).scaled(sw, sh, Qt::IgnoreAspectRatio, Qt::FastTransformation);
    QImage big = small.scaled(r.size(), Qt::IgnoreAspectRatio, Qt::FastTransformation);
    QPainter p(&img);
    p.drawImage(r.topLeft(), big);
}

// 画箭头（线段 + 实心三角头），并返回线段应当缩短的长度
qreal drawArrowHead(QPainter& p, const QPointF& from, const QPointF& to,
                    qreal width, const QColor& color) {
    const qreal dx = to.x() - from.x();
    const qreal dy = to.y() - from.y();
    const qreal len = std::hypot(dx, dy);
    if (len < 1.0) return 0.0;
    const qreal angle = std::atan2(dy, dx);
    qreal head = std::max<qreal>(10.0, width * 4.5);
    if (head > len * 0.8) head = len * 0.8;
    const qreal spread = 0.42;   // 约 24 度

    QPointF a1(to.x() - head * std::cos(angle - spread), to.y() - head * std::sin(angle - spread));
    QPointF a2(to.x() - head * std::cos(angle + spread), to.y() - head * std::sin(angle + spread));
    QPolygonF tri;
    tri << to << a1 << a2;

    p.save();
    p.setPen(Qt::NoPen);
    p.setBrush(color);          // 明确用标注颜色，别依赖 pen
    p.drawPolygon(tri);
    p.restore();
    return head * 0.85;         // 线段缩进，避免从箭头尖冒出
}

} // namespace

namespace annot {

Annotation fromDrag(Tool t, const QPointF& a, const QPointF& b, const QColor& c, qreal w) {
    Annotation an;
    an.type = t;
    an.color = c;
    an.width = w;
    if (t == Tool::Arrow || t == Tool::Line) {
        an.pts << a << b;
    } else {
        an.pts << a << b;   // 两个对角点
    }
    return an;
}

void renderToImage(QImage& canvas, const QVector<Annotation>& list, int skipIndex) {
    QPainter p(&canvas);
    p.setRenderHint(QPainter::Antialiasing, true);
    p.setRenderHint(QPainter::TextAntialiasing, true);

    for (int i = 0; i < list.size(); ++i) {
        if (i == skipIndex) continue;
        const Annotation& an = list[i];
        if (an.pts.isEmpty()) continue;

        QPen pen(an.color, an.width, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin);

        switch (an.type) {
        case Tool::Rect: {
            QRectF r = QRectF(an.pts.first(), an.pts.last()).normalized();
            p.setPen(pen);
            p.setBrush(Qt::NoBrush);
            p.drawRoundedRect(r, 3, 3);
            break;
        }
        case Tool::Ellipse: {
            QRectF r = QRectF(an.pts.first(), an.pts.last()).normalized();
            p.setPen(pen);
            p.setBrush(Qt::NoBrush);
            p.drawEllipse(r);
            break;
        }
        case Tool::Line: {
            if (an.pts.size() < 2) break;
            p.setPen(pen);
            p.drawLine(an.pts.first(), an.pts.last());
            break;
        }
        case Tool::Arrow: {
            if (an.pts.size() < 2) break;
            const QPointF a = an.pts.first();
            const QPointF b = an.pts.last();
            QPen ap(an.color, an.width, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin);
            p.setPen(ap);
            p.setBrush(Qt::NoBrush);
            const qreal cut = drawArrowHead(p, a, b, an.width, an.color);
            const qreal len = std::hypot(b.x() - a.x(), b.y() - a.y());
            if (len > cut) {
                const qreal t = (len - cut) / len;
                p.drawLine(a, QPointF(a.x() + (b.x() - a.x()) * t, a.y() + (b.y() - a.y()) * t));
            }
            break;
        }
        case Tool::Pen: {
            if (an.pts.size() < 2) break;
            QPen pp = pen;
            p.setPen(pp);
            p.setBrush(Qt::NoBrush);
            p.drawPath(smoothPath(an.pts));
            break;
        }
        case Tool::Highlight: {
            if (an.pts.size() < 2) break;
            QColor c = an.color;
            c.setAlpha(90);
            QPen hp(c, an.width * 6.0, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin);
            p.setPen(hp);
            p.setBrush(Qt::NoBrush);
            p.drawLine(an.pts.first(), an.pts.last());
            break;
        }
        case Tool::Mosaic: {
            int cell = std::max(4, int(an.width * 3));
            QVector<QRect> regions;
            if (an.pts.size() <= 2) {
                regions.append(QRectF(an.pts.first(), an.pts.last()).normalized().toRect());
            } else {
                // 笔刷模式：沿轨迹铺方块
                const int r = std::max(4, int(an.width * 2));
                for (int k = 1; k < an.pts.size(); ++k) {
                    QPointF a = an.pts[k - 1], b = an.pts[k];
                    qreal dist = std::hypot(b.x() - a.x(), b.y() - a.y());
                    int steps = std::max(1, int(dist / std::max(1.0, r * 0.8)));
                    for (int i = 0; i <= steps; ++i) {
                        qreal t = double(i) / steps;
                        QPointF c = a + (b - a) * t;
                        regions.append(QRect(int(c.x() - r), int(c.y() - r), r * 2, r * 2));
                    }
                }
            }
            // 不能在原 QImage 上嵌套 QPainter，先结束
            p.end();
            for (const QRect& rc : regions) pixelate(canvas, rc, cell);
            p.begin(&canvas);
            p.setRenderHint(QPainter::Antialiasing, true);
            p.setRenderHint(QPainter::TextAntialiasing, true);
            break;
        }
        case Tool::Text: {
            if (an.text.isEmpty()) break;
            QFont f = p.font();
            int px = std::max(12, int(an.width * 6));
            f.setPixelSize(px);
            f.setBold(true);
            p.setFont(f);
            QFontMetricsF fm(f);
            QRectF br = fm.boundingRect(QRectF(0, 0, 4000, 4000), Qt::TextWordWrap, an.text);
            QRectF box(an.pts.first(), br.size() + QSizeF(8, 4));
            p.setPen(Qt::NoPen);
            p.setBrush(QColor(0, 0, 0, 90));
            p.drawRoundedRect(box.adjusted(-4, -2, 4, 2), 4, 4);
            p.setPen(an.color);
            p.drawText(box, Qt::TextWordWrap, an.text);
            break;
        }
        case Tool::Number: {
            QFont f = p.font();
            int px = std::max(14, int(an.width * 7));
            f.setPixelSize(px);
            f.setBold(true);
            p.setFont(f);
            qreal rad = px * 0.75;
            QPointF c = an.pts.first();
            p.setPen(Qt::NoPen);
            p.setBrush(an.color);
            p.drawEllipse(c, rad, rad);
            p.setPen(Qt::white);
            p.drawText(QRectF(c.x() - rad, c.y() - rad, rad * 2, rad * 2), Qt::AlignCenter,
                       QString::number(an.number));
            break;
        }
        default: break;
        }
    }
}

} // namespace annot
