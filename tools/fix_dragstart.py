import io

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
old = """    if (m_tool == Tool::None || m_tool == Tool::Select) {
        m_drag = DragMove;
        m_dragStart = pos;
        m_selStart = m_sel;
        return;
    }"""
new = """    if (m_tool == Tool::None || m_tool == Tool::Select) {
        m_drag = DragMove;
        m_dragStart = pos;
        m_dragStartF = e->position();   // 必须记录浮点按下点，否则位移算错（选区会跳走）
        m_selStart = m_sel;
        return;
    }"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("m_dragStartF fixed")
else:
    print("MISS")
