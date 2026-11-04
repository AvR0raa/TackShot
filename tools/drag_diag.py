import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
old = """                ov->demoSimMove(QPoint(grip.x() + 40, grip.y() + 30));"""
new = """                log << QString("  annotPress dpr=%1 count=%2 selected=%3")
                           .arg(dpr).arg(ov->demoAnnotCount()).arg(ov->demoSelected());
                ov->demoSimMove(QPoint(grip.x() + 40, grip.y() + 30));"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("diag added")
else:
    print("MISS")
