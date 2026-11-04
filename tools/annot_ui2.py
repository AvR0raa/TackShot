import io

# ---------- overlay.h：补充状态与模式 ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    enum DragMode { DragNone, DragSelect, DragMove, DragResize, DragDraw };",
              "    enum DragMode { DragNone, DragSelect, DragMove, DragResize, DragDraw, DragAnnot, DragAnnotResize };")
s = s.replace("    bool     m_movingAnnot = false;\n    QRectF   m_annotStartBox;",
"""    bool     m_movingAnnot = false;
    QRectF   m_annotStartBox;
    QVector<QPointF> m_annotPtsStart;
    QPoint   m_lastDragPos;""")
io.open(p, "w", encoding="utf-8").write(s)

# ---------- overlay.cpp ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()

# 1) press：优先命中已选标注的手柄 / 已存在标注
old = """    int h = handleAt(pos);
    if (h >= 0) {
        m_drag = DragResize;
        m_resizeHandle = h;
        m_selStart = m_sel;
        m_dragStart = pos;
        return;
    }"""
new = """    // 1) 已选标注的缩放手柄
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
        if (hit >= 0 && (m_tool == Tool::None || hit == m_selected)) {
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
        if (hit < 0 && m_tool == Tool::None) m_selected = -1;
    }

    int h = handleAt(pos);
    if (h >= 0) {
        m_drag = DragResize;
        m_resizeHandle = h;
        m_selStart = m_sel;
        m_dragStart = pos;
        return;
    }"""
if old in s:
    s = s.replace(old, new, 1)

# 2) move：处理拖动/缩放
old_move = """    if (m_drag == DragMove) {"""
new_move = """    if (m_drag == DragAnnot && m_selected >= 0 && m_selected < m_annots.size()) {
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
    if (m_drag == DragMove) {"""
if old_move in s:
    s = s.replace(old_move, new_move, 1)

# 3) release：结束标注拖动/缩放并记录撤销
old_rel = """    if (m_drag == DragDraw) {"""
new_rel = """    if (m_drag == DragAnnot || m_drag == DragAnnotResize) {
        m_drag = DragNone;
        m_annotHandle = -1;
        pushHistory();
        update();
        return;
    }
    if (m_drag == DragDraw) {"""
if old_rel in s:
    s = s.replace(old_rel, new_rel, 1)

# 4) Delete 删除选中
s = s.replace("""    if (e->key() == Qt::Key_Escape) {""",
"""    if ((e->key() == Qt::Key_Delete || e->key() == Qt::Key_Backspace) &&
        m_selected >= 0 && m_selected < m_annots.size()) {
        m_annots.removeAt(m_selected);
        m_selected = -1;
        pushHistory();
        update();
        return;
    }
    if (e->key() == Qt::Key_Escape) {""")

# 5) 自检用的鼠标注入
s = s.replace("QVector<int> Overlay::demoUndoTest() {",
"""void Overlay::demoSimPress(const QPoint& p) {
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

QVector<int> Overlay::demoUndoTest() {""")
io.open(p, "w", encoding="utf-8").write(s)
print("annotation move/resize/delete added")
