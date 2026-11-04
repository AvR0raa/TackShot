import io

# overlay.h：记录浮点按下点
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.h"
s = io.open(p, encoding="utf-8").read()
if "m_dragStartF" not in s:
    s = s.replace("    QPoint   m_lastDragPos;", "    QPoint   m_lastDragPos;\n    QPointF  m_dragStartF;")
io.open(p, "w", encoding="utf-8").write(s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()

# press 时记录浮点起点
s = s.replace("""        m_drag = DragMove;
        m_selStart = m_sel;
        m_dragStart = pos;""",
"""        m_drag = DragMove;
        m_selStart = m_sel;
        m_dragStart = pos;
        m_dragStartF = e->position();""")
s = s.replace("""        m_drag = DragResize;
        m_resizeHandle = h;
        m_selStart = m_sel;
        m_dragStart = pos;""",
"""        m_drag = DragResize;
        m_resizeHandle = h;
        m_selStart = m_sel;
        m_dragStart = pos;
        m_dragStartF = e->position();""")

# DragMove：用浮点位置一次取整，减少 ±1 抖动
s = s.replace("""    if (m_drag == DragMove) {
        QPoint d = e->pos() - m_dragStart;
        QRect r = m_selStart.translated(qRound(d.x() * m_scale), qRound(d.y() * m_scale));
        m_sel = r.intersected(m_shot.rect());
        placeToolbar();
        update();
        return;
    }""",
"""    if (m_drag == DragMove) {
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
    }""")

# DragResize：同样用浮点
s = s.replace("""        QRect r = m_selStart;
        QPoint d(qRound((e->pos().x() - m_dragStart.x()) * m_scale),
                 qRound((e->pos().y() - m_dragStart.y()) * m_scale));""",
"""        QRect r = m_selStart;
        const QPointF df = (e->position() - m_dragStartF) * m_scale;
        QPoint d(qRound(df.x()), qRound(df.y()));""")
io.open(p, "w", encoding="utf-8").write(s)
print("drag smoothing applied")
