import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
old = """            log << QString("dpr=%1 start=%2,%3 movedTo=%4,%5 expectedX=%6 dy=%7 sizeOk=%8 back=%9 pass=%10")"""
new = """            // ---- 缩放手柄：拖右下角，尺寸应按位移增长 ----
            bool resizePass = false;
            {
                QRect cur = ov->demoSel();   // 已移动后的选区
                QPoint br(qRound((cur.x() + cur.width() - 1) / dpr),
                          qRound((cur.y() + cur.height() - 1) / dpr));
                ov->demoSimPress(br);
                ov->demoSimMove(QPoint(br.x() + 30, br.y() + 20));
                QRect after = ov->demoSel();
                resizePass = (after.width() == cur.width() + qRound(30 * dpr)) ||
                             qAbs(after.width() - (cur.width() + qRound(30 * dpr))) <= 2;
                ov->demoSimRelease(QPoint(br.x() + 30, br.y() + 20));
                log << QString("  resize dpr=%1 %2x%3 -> %4x%5 pass=%6")
                           .arg(dpr).arg(cur.width()).arg(cur.height())
                           .arg(after.width()).arg(after.height())
                           .arg(resizePass ? "true" : "false");
            }
            pass = pass && resizePass;
            allPass &= resizePass;

            // ---- 标注拖动：画一个矩形，再整体拖走 ----
            bool annotPass = false;
            {
                ov->demoSetTool(Tool::Rect);
                ov->demoSimPress(QPoint(100, 100));
                ov->demoSimMove(QPoint(200, 180));
                ov->demoSimRelease(QPoint(200, 180));
                int n0 = ov->demoAnnotCount();
                ov->demoSetTool(Tool::Select);
                ov->demoSimPress(QPoint(150, 140));
                QRect before = QRect(0, 0, 0, 0);
                if (ov->demoAnnotCount() > 0) {
                    Annotation a0 = ov->demoAnnot(n0 - 1);
                    if (a0.pts.size() >= 2) before = QRectF(a0.pts[0], a0.pts[1]).toRect();
                }
                ov->demoSimMove(QPoint(190, 170));
                ov->demoSimRelease(QPoint(190, 170));
                QRect after(0, 0, 0, 0);
                if (ov->demoAnnotCount() > 0) {
                    Annotation a1 = ov->demoAnnot(n0 - 1);
                    if (a1.pts.size() >= 2) after = QRectF(a1.pts[0], a1.pts[1]).toRect();
                }
                annotPass = before.isValid() && after.isValid() &&
                            qAbs((after.x() - before.x()) - qRound(40 * dpr)) <= 2;
                log << QString("  annotMove dpr=%1 %2,%3 -> %4,%5 pass=%6")
                           .arg(dpr).arg(before.x()).arg(before.y())
                           .arg(after.x()).arg(after.y()).arg(annotPass ? "true" : "false");
            }
            pass = pass && annotPass;
            allPass &= annotPass;

            log << QString("dpr=%1 start=%2,%3 movedTo=%4,%5 expectedX=%6 dy=%7 sizeOk=%8 back=%9 pass=%10")"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("resize + annot drag tests added")
else:
    print("MISS")
