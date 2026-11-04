import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\capture.cpp"
s = io.open(p, encoding="utf-8").read()

# 1) 修正 lastPath 标注
s = s.replace("    if (physicalRectOut) *physicalRectOut = v;\n    g_lastPath = QStringLiteral(\"dxgi\");\n    return img;\n}\n\nQImage captureRect",
              "    if (physicalRectOut) *physicalRectOut = v;\n    return img;\n}\n\nQImage captureRect")

# 2) 兜底路径按物理像素抓（grabWindow 给的是逻辑尺寸，会只有 80% 内容）
old = """    QVector<Surface> surfaces;
    for (QScreen* s : QGuiApplication::screens()) {
        QPixmap pm = s->grabWindow(0);
        if (pm.isNull()) continue;
        QImage img = pm.toImage();
        const qreal dpr = s->devicePixelRatio();
        QRect g = s->geometry();
        QRect pr(QPoint(qRound(g.x() * dpr), qRound(g.y() * dpr)), img.size());
        surfaces.push_back({pr, img});
    }"""
new = """    QVector<Surface> surfaces;
    for (QScreen* s : QGuiApplication::screens()) {
        const qreal dpr = s->devicePixelRatio();
        QRect g = s->geometry();
        QRect phys(QPoint(qRound(g.x() * dpr), qRound(g.y() * dpr)),
                   QSize(qRound(g.width() * dpr), qRound(g.height() * dpr)));
        // 优先用 GDI 直接按物理像素抓（BitBlt 走的是物理坐标系）
        QImage img = captureRect(phys);
        if (img.isNull() || img.size() != phys.size()) {
            QPixmap pm = s->grabWindow(0);
            if (pm.isNull()) continue;
            QImage alt = pm.toImage();
            if (alt.size() != phys.size())
                alt = alt.scaled(phys.size(), Qt::IgnoreAspectRatio, Qt::SmoothTransformation);
            img = alt;
        }
        surfaces.push_back({phys, img});
    }"""
if old in s:
    s = s.replace(old, new, 1)

# 3) DXGI 成功时标注路径
s = s.replace("""    QRect v;
    QImage img = compose(surfaces, v);
    if (physicalRectOut) *physicalRectOut = v;
    return img;
}

QRect nativeMonitorRect""",
"""    QRect v;
    QImage img = compose(surfaces, v);
    if (physicalRectOut) *physicalRectOut = v;
    g_lastPath = QStringLiteral("dxgi");
    return img;
}

QRect nativeMonitorRect""")
io.open(p, "w", encoding="utf-8").write(s)
print("fallback now physical")
