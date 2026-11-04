import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("""    m_bar->hide();
    updateToolButtons();
    layout()->activate();""",
"""    m_bar->hide();
    updateToolButtons();
    m_bar->adjustSize();""")
io.open(p, "w", encoding="utf-8").write(s)
print("null layout crash fixed")
