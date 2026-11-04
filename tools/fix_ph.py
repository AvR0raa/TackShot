import io, re
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.cpp"
s = io.open(p, encoding="utf-8").read()
start = s.index("m_trGlossary->setPlaceholderText(")
end = s.index("));", start) + 3
good = 'm_trGlossary->setPlaceholderText(QStringLiteral("术语表，每行一条：原文=译法（例如 TackShot=TackShot）"));'
s = s[:start] + good + s[end:]
io.open(p, "w", encoding="utf-8").write(s)
print("placeholder fixed")
