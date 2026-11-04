import io

# ---------------- annotate.h：加 Select 工具 ----------------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\annotate.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("enum class Tool {\n    None = 0, Rect, Ellipse, Arrow, Line, Pen, Highlight, Mosaic, Text, Number\n};",
              "enum class Tool {\n    None = 0, Rect, Ellipse, Arrow, Line, Pen, Highlight, Mosaic, Text, Number, Select\n};")
io.open(p, "w", encoding="utf-8").write(s)

# ---------------- annotate.cpp：平滑笔迹 ----------------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\annotate.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("namespace {\n\nvoid pixelate(",
"""namespace {

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

void pixelate(""")
s = s.replace("""        case Tool::Pen: {
            if (an.pts.size() < 2) break;
            QPen pp = pen;
            p.setPen(pp);
            p.setBrush(Qt::NoBrush);
            p.drawPolyline(an.pts.constData(), an.pts.size());
            break;
        }""",
"""        case Tool::Pen: {
            if (an.pts.size() < 2) break;
            QPen pp = pen;
            p.setPen(pp);
            p.setBrush(Qt::NoBrush);
            p.drawPath(smoothPath(an.pts));
            break;
        }""")
io.open(p, "w", encoding="utf-8").write(s)
print("smooth pen + select tool")
