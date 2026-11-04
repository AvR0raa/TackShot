import io

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.h"
s = io.open(p, encoding="utf-8").read()
if "demoHitTest" not in s:
    s = s.replace("    QRect demoSel() const { return m_sel; }",
                  "    QRect demoSel() const { return m_sel; }\n    int demoHitTest(const QPoint& p) const { return hitAnnot(toLocal(p)); }\n    QPointF demoToLocal(const QPoint& p) const { return toLocal(p); }\n    QRect demoAnnotBounds(int i) const { return m_annots.value(i).pts.isEmpty() ? QRect() : annotBounds(m_annots.value(i)).toRect(); }")
io.open(p, "w", encoding="utf-8").write(s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("""                log << QString("  annotPress dpr=%1 count=%2 selected=%3")
                           .arg(dpr).arg(ov->demoAnnotCount()).arg(ov->demoSelected());""",
"""                {
                    QPointF lc = ov->demoToLocal(grip);
                    log << QString("  annotPress dpr=%1 count=%2 selected=%3 grip=%4,%5 local=%6,%7 "
                                   "hit=%8 sel=%9,%10 %11x%12 annotBounds=%13,%14 %15x%16")
                               .arg(dpr).arg(ov->demoAnnotCount()).arg(ov->demoSelected())
                               .arg(grip.x()).arg(grip.y())
                               .arg(lc.x()).arg(lc.y()).arg(ov->demoHitTest(grip))
                               .arg(ov->demoSel().x()).arg(ov->demoSel().y())
                               .arg(ov->demoSel().width()).arg(ov->demoSel().height())
                               .arg(ov->demoAnnotBounds(0).x()).arg(ov->demoAnnotBounds(0).y())
                               .arg(ov->demoAnnotBounds(0).width()).arg(ov->demoAnnotBounds(0).height());
                }""")
io.open(p, "w", encoding="utf-8").write(s)
print("hit diag added")
