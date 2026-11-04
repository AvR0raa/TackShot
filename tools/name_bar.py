import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
if 'setObjectName("toolbar")' not in s:
    s = s.replace("    m_bar = new QWidget(this);", "    m_bar = new QWidget(this);\n    m_bar->setObjectName(QStringLiteral(\"toolbar\"));")
io.open(p, "w", encoding="utf-8").write(s)
print("toolbar named")
