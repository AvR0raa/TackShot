import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace(".arg(QStringLiteral(APP_VERSION))));", ".arg(QString::fromUtf8(APP_VERSION))));")
io.open(p, "w", encoding="utf-8").write(s)
print("fixed")
