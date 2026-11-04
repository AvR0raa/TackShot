import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
old = """                ov->demoSetTool(Tool::Rect);
                ov->demoSimPress(QPoint(100, 100));
                ov->demoSimMove(QPoint(200, 180));
                ov->demoSimRelease(QPoint(200, 180));"""
new = """                // 必须在选区内画，否则会变成重新拉框
                QRect s0 = ov->demoSel();
                QPoint p0(qRound((s0.x() + 40) / dpr), qRound((s0.y() + 40) / dpr));
                QPoint p1(qRound((s0.x() + 240) / dpr), qRound((s0.y() + 160) / dpr));
                ov->demoSetTool(Tool::Rect);
                ov->demoSimPress(p0);
                ov->demoSimMove(p1);
                ov->demoSimRelease(p1);"""
if old in s:
    s = s.replace(old, new, 1)
    s = s.replace("""                ov->demoSetTool(Tool::Select);
                ov->demoSimPress(QPoint(150, 140));""",
"""                ov->demoSetTool(Tool::Select);
                QPoint grip(qRound((s0.x() + 140) / dpr), qRound((s0.y() + 100) / dpr));
                ov->demoSimPress(grip);""")
    s = s.replace("""                ov->demoSimMove(QPoint(190, 170));
                ov->demoSimRelease(QPoint(190, 170));""",
"""                ov->demoSimMove(QPoint(grip.x() + 40, grip.y() + 30));
                ov->demoSimRelease(QPoint(grip.x() + 40, grip.y() + 30));""")
    s = s.replace("""                annotPass = before.isValid() && after.isValid() &&
                            qAbs((after.x() - before.x()) - qRound(40 * dpr)) <= 2;""",
"""                annotPass = !before.isNull() && !after.isNull() &&
                            qAbs((after.x() - before.x()) - qRound(40 * dpr)) <= 3 &&
                            qAbs((after.y() - before.y()) - qRound(30 * dpr)) <= 3;""")
    io.open(p, "w", encoding="utf-8").write(s)
    print("annot test fixed")
else:
    print("MISS")
