import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()

old = """        // 尺寸标签
        QString sizeText = QStringLiteral("%1 × %2").arg(m_sel.width()).arg(m_sel.height());
        QFont f = font();
        f.setPixelSize(12);
        p.setFont(f);
        QFontMetrics fm(f);
        int tw = fm.horizontalAdvance(sizeText) + 12;
        QRect tag(sel.left(), sel.top() - 24, tw, 20);
        if (tag.top() < 0) tag.moveTop(sel.top() + 4);
        p.setPen(Qt::NoPen);
        p.setBrush(QColor(0, 0, 0, 160));
        p.drawRoundedRect(tag, 4, 4);
        p.setPen(QColor("#e8eaed"));
        p.drawText(tag, Qt::AlignCenter, sizeText);"""
new = """        // 尺寸标签（圆角胶囊）
        QString sizeText = QStringLiteral("%1 × %2").arg(m_sel.width()).arg(m_sel.height());
        QFont f = font();
        f.setPixelSize(12);
        p.setFont(f);
        QFontMetrics fm(f);
        int tw = fm.horizontalAdvance(sizeText) + 18;
        QRectF tag(sel.left(), sel.top() - 28, tw, 22);
        if (tag.top() < 2) tag.moveTop(sel.top() + 6);
        p.setPen(QPen(QColor(255, 255, 255, 30), 1));
        p.setBrush(QColor(18, 20, 24, 235));
        p.drawRoundedRect(tag, 11, 11);
        p.setPen(QColor("#e8eaed"));
        p.drawText(tag, Qt::AlignCenter, sizeText);"""
if old in s:
    s = s.replace(old, new, 1)

# 手柄：圆形 + 双层描边，更清晰
old2 = """            p.setPen(QPen(Qt::white, 1));
            p.setBrush(QColor("#2f6fed"));
            const int hs = 4;
            QPoint pts[8] = {sel.topLeft(), QPoint(sel.center().x(), sel.top()), sel.topRight(),
                             QPoint(sel.right(), sel.center().y()), sel.bottomRight(),
                             QPoint(sel.center().x(), sel.bottom()), sel.bottomLeft(),
                             QPoint(sel.left(), sel.center().y())};
            for (int i = 0; i < 8; ++i)
                p.drawRect(QRect(pts[i].x() - hs, pts[i].y() - hs, hs * 2, hs * 2));"""
new2 = """            const qreal hs = 4.5;
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
                p.drawEllipse(pts[i], hs, hs);"""
if old2 in s:
    s = s.replace(old2, new2, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("badge + handles polished")
