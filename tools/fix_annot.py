import io

# ---------- annotate.cpp：修箭头 + 马赛克支持笔刷轨迹 ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\annotate.cpp"
s = io.open(p, encoding="utf-8").read()

old_arrow = """void drawArrowHead(QPainter& p, const QPointF& from, const QPointF& to, qreal w) {
    QLineF line(from, to);
    double angle = std::atan2(-line.dy(), line.dx());
    qreal head = std::max<qreal>(10.0, w * 4.0);
    qreal spread = M_PI / 7.0;
    QPointF p1 = to - QPointF(std::cos(angle - spread) * head, -std::sin(angle - spread) * head);
    QPointF p2 = to - QPointF(std::cos(angle + spread) * head, -std::sin(angle + spread) * head);
    QPolygonF poly;
    poly << to << p1 << p2;
    p.save();
    p.setPen(Qt::NoPen);
    p.setBrush(p.pen().color());
    p.drawPolygon(poly);
    p.restore();
}"""
new_arrow = """// 画箭头（线段 + 实心三角头），并返回线段应当缩短的长度
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
}"""
if old_arrow in s:
    s = s.replace(old_arrow, new_arrow, 1)

old_arrow_case = """        case Tool::Arrow: {
            if (an.pts.size() < 2) break;
            QPen ap = pen;
            p.setPen(ap);
            p.drawLine(an.pts.first(), an.pts.last());
            p.setBrush(an.color);
            drawArrowHead(p, an.pts.first(), an.pts.last(), an.width);
            break;
        }"""
new_arrow_case = """        case Tool::Arrow: {
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
        }"""
if old_arrow_case in s:
    s = s.replace(old_arrow_case, new_arrow_case, 1)

# 马赛克：>2 个点时按笔刷轨迹铺像素块
old_mosaic = """        case Tool::Mosaic: {
            QRectF r = QRectF(an.pts.first(), an.pts.last()).normalized();
            QRect ir = r.toRect();
            int cell = std::max(4, int(an.width * 3));
            // 不能在同一 QImage 上嵌套 QPainter，先结束当前绘制
            p.end();
            pixelate(canvas, ir, cell);
            p.begin(&canvas);
            p.setRenderHint(QPainter::Antialiasing, true);
            p.setRenderHint(QPainter::TextAntialiasing, true);
            break;
        }"""
new_mosaic = """        case Tool::Mosaic: {
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
        }"""
if old_mosaic in s:
    s = s.replace(old_mosaic, new_mosaic, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("arrow + mosaic fixed")
