import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
old = """            const QPoint press(700, 500);           // 位于选区内（逻辑坐标）"""
new = """            // 按下点必须落在“选区在控件里的位置”内：图像坐标 / dpr
            const QPoint press(qRound(startSel.center().x() / dpr),
                               qRound(startSel.center().y() / dpr));"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("press point fixed")
else:
    print("MISS")
