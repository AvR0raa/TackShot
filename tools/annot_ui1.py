import io

# ---------- overlay.h ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    QImage demoFinal() const { return renderFinal(); }",
"""    QImage demoFinal() const { return renderFinal(); }

    // 自检钩子：设置工具、模拟鼠标、读取标注
    void demoSetTool(Tool t) { m_tool = t; updateToolButtons(); }
    void demoSelect(const QRect& sel) { m_sel = sel; m_phase = Editing; update(); }
    void demoSimPress(const QPoint& p);
    void demoSimMove(const QPoint& p);
    void demoSimRelease(const QPoint& p);
    int demoAnnotCount() const { return m_annots.size(); }
    Annotation demoAnnot(int i) const { return m_annots.value(i); }
    int demoSelected() const { return m_selected; }""")

s = s.replace("    QVector<Annotation> m_annots;",
"""    QVector<Annotation> m_annots;
    int      m_selected = -1;          // 当前选中的标注
    int      m_annotHandle = -1;       // 0..7 缩放手柄
    bool     m_movingAnnot = false;
    QRectF   m_annotStartBox;
    void     drawAnnotHandles(QPainter& p);
    QRectF   annotBounds(const Annotation& a) const;
    int      hitAnnot(const QPointF& local) const;""")
io.open(p, "w", encoding="utf-8").write(s)

# ---------- overlay.cpp ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("#include <QTransform>", "#include <QTransform>")
s = s.replace('#include "secrets.h"', '#include "secrets.h"\n#include <QPropertyAnimation>\n#include <QAbstractAnimation>')

# 淡入
s = s.replace("""    setGeometry(logical);
    buildToolbar();""",
"""    setGeometry(logical);
    buildToolbar();

    // 淡入，避免“啪”地一下出现
    setWindowOpacity(0.0);
    auto* fade = new QPropertyAnimation(this, "windowOpacity", this);
    fade->setDuration(110);
    fade->setStartValue(0.0);
    fade->setEndValue(1.0);
    fade->setEasingCurve(QEasingCurve::OutCubic);
    fade->start(QAbstractAnimation::DeleteWhenStopped);""")

# 辅助函数
s = s.replace("QRect Overlay::selRectWidget() const {",
"""QRectF Overlay::annotBounds(const Annotation& a) const {
    if (a.pts.isEmpty()) return QRectF();
    QRectF r(a.pts.first(), a.pts.first());
    for (const QPointF& p : a.pts) r = r.united(QRectF(p, p));
    if (a.type == Tool::Text) {
        QFont f;
        f.setPixelSize(std::max(12, int(a.width * 6)));
        QFontMetricsF fm(f);
        QRectF br = fm.boundingRect(QRectF(0, 0, 4000, 4000), Qt::TextWordWrap, a.text);
        r.setSize(br.size() + QSizeF(16, 6));
    } else if (a.type == Tool::Number) {
        qreal rad = std::max(14, int(a.width * 7)) * 0.75;
        r = QRectF(a.pts.first().x() - rad, a.pts.first().y() - rad, rad * 2, rad * 2);
    }
    if (r.width() < 6) r.setWidth(6);
    if (r.height() < 6) r.setHeight(6);
    return r;
}

int Overlay::hitAnnot(const QPointF& local) const {
    for (int i = m_annots.size() - 1; i >= 0; --i) {
        if (annotBounds(m_annots[i]).adjusted(-4, -4, 4, 4).contains(local)) return i;
    }
    return -1;
}

QRect Overlay::selRectWidget() const {""")

# 绘制选中框
s = s.replace("""    // 放大镜
    if (m_hasCursor && (m_phase == Selecting)) {""",
"""    // 选中标注的控制框
    if (m_selected >= 0 && m_selected < m_annots.size()) {
        QRectF b = annotBounds(m_annots[m_selected]);
        QRectF wb(b.x() / m_scale + selRectWidget().x(), b.y() / m_scale + selRectWidget().y(),
                  b.width() / m_scale, b.height() / m_scale);
        p.setPen(QPen(QColor("#00c8ff"), 1, Qt::DashLine));
        p.setBrush(Qt::NoBrush);
        p.drawRect(wb);
        p.setPen(QPen(Qt::white, 1));
        p.setBrush(QColor("#00c8ff"));
        const QPointF pts[8] = {wb.topLeft(), QPointF(wb.center().x(), wb.top()), wb.topRight(),
                                QPointF(wb.right(), wb.center().y()), wb.bottomRight(),
                                QPointF(wb.center().x(), wb.bottom()), wb.bottomLeft(),
                                QPointF(wb.left(), wb.center().y())};
        for (const QPointF& q : pts) p.drawRect(QRectF(q.x() - 4, q.y() - 4, 8, 8));
    }

    // 放大镜
    if (m_hasCursor && (m_phase == Selecting)) {""")
io.open(p, "w", encoding="utf-8").write(s)
print("overlay scaffolding added")
