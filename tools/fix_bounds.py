import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
old = """    if (a.pts.isEmpty()) return QRectF();
    QRectF r(a.pts.first(), a.pts.first());
    for (const QPointF& p : a.pts) r = r.united(QRectF(p, p));"""
new = """    if (a.pts.isEmpty()) return QRectF();
    // 注意：QRectF(p,p) 是“空矩形”，united() 会忽略它，两个点的标注会算成 0 尺寸。
    // 这里直接按 min/max 求包围盒。
    qreal minX = a.pts.first().x(), maxX = minX;
    qreal minY = a.pts.first().y(), maxY = minY;
    for (const QPointF& p : a.pts) {
        minX = qMin(minX, p.x()); maxX = qMax(maxX, p.x());
        minY = qMin(minY, p.y()); maxY = qMax(maxY, p.y());
    }
    QRectF r(minX, minY, maxX - minX, maxY - minY);"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("annotBounds fixed")
else:
    print("MISS")
