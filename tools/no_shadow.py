import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
old = """    // 阴影
    auto* shadow = new QGraphicsDropShadowEffect(m_bar);
    shadow->setBlurRadius(24);
    shadow->setOffset(0, 6);
    shadow->setColor(QColor(0, 0, 0, 160));
    m_bar->setGraphicsEffect(shadow);

"""
if old in s:
    s = s.replace(old, "", 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("shadow removed")
else:
    print("MISS shadow")
