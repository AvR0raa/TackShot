import io

# ---------- overlay.h ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    QSpinBox*   m_widthBox = nullptr;",
              "    QLabel*     m_widthLabel = nullptr;\n    void setWidth(int w);")
io.open(p, "w", encoding="utf-8").write(s)

# ---------- overlay.cpp ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()

# 1) 工具列表加“选择”，并改宽度控件
old_tools = """    const QVector<Tool> tools = {Tool::Rect, Tool::Ellipse, Tool::Arrow, Tool::Line,
                                 Tool::Pen, Tool::Highlight, Tool::Mosaic, Tool::Text, Tool::Number};"""
new_tools = """    const QVector<Tool> tools = {Tool::Select, Tool::Rect, Tool::Ellipse, Tool::Arrow, Tool::Line,
                                 Tool::Pen, Tool::Highlight, Tool::Mosaic, Tool::Text, Tool::Number};"""
if old_tools in s:
    s = s.replace(old_tools, new_tools, 1)

old_w = """    m_widthBox = new QSpinBox(m_bar);
    m_widthBox->setRange(1, 24);
    m_widthBox->setValue(int(m_width));
    m_widthBox->setFixedWidth(46);
    connect(m_widthBox, QOverload<int>::of(&QSpinBox::valueChanged), this, [this](int v) {
        m_width = v;
        Config::get().penWidth = v;
    });
    lay->addWidget(m_widthBox);"""
new_w = """    auto* minus = new QToolButton(m_bar);
    minus->setText(QStringLiteral("−"));
    minus->setAutoRaise(true);
    minus->setStyleSheet("QToolButton { color:#dfe3e8; padding:2px 8px; }");
    connect(minus, &QToolButton::clicked, this, [this]() { setWidth(int(m_width) - 1); });
    lay->addWidget(minus);

    m_widthLabel = new QLabel(QString::number(int(m_width)), m_bar);
    m_widthLabel->setFixedWidth(18);
    m_widthLabel->setAlignment(Qt::AlignCenter);
    m_widthLabel->setStyleSheet("color:#dfe3e8;");
    lay->addWidget(m_widthLabel);

    auto* plus = new QToolButton(m_bar);
    plus->setText(QStringLiteral("+"));
    plus->setAutoRaise(true);
    plus->setStyleSheet("QToolButton { color:#dfe3e8; padding:2px 8px; }");
    connect(plus, &QToolButton::clicked, this, [this]() { setWidth(int(m_width) + 1); });
    lay->addWidget(plus);"""
if old_w in s:
    s = s.replace(old_w, new_w, 1)

# 2) setWidth 实现（夹紧 1..24，避免 0 或负值）
s = s.replace("void Overlay::updateToolButtons() {",
"""void Overlay::setWidth(int w) {
    w = qBound(1, w, 24);
    m_width = w;
    Config::get().penWidth = w;
    if (m_widthLabel) m_widthLabel->setText(QString::number(w));
    update();
}

void Overlay::updateToolButtons() {""")

# 3) 工具按钮顺序数组同步
s = s.replace("""    const QVector<Tool> order = {Tool::Rect, Tool::Ellipse, Tool::Arrow, Tool::Line,
                                 Tool::Pen, Tool::Highlight, Tool::Mosaic, Tool::Text, Tool::Number};""",
"""    const QVector<Tool> order = {Tool::Select, Tool::Rect, Tool::Ellipse, Tool::Arrow, Tool::Line,
                                 Tool::Pen, Tool::Highlight, Tool::Mosaic, Tool::Text, Tool::Number};""")

# 4) Select 工具图标
s = s.replace("""    case Tool::Number:   p.drawEllipse(QRectF(4, 4, 14, 14)); break;""",
"""    case Tool::Number:   p.drawEllipse(QRectF(4, 4, 14, 14)); break;
    case Tool::Select: {
        QPolygonF arrow;
        arrow << QPointF(6, 4) << QPointF(6, 17) << QPointF(10, 13) << QPointF(13, 19)
              << QPointF(16, 17.5) << QPointF(13, 12) << QPointF(18, 11);
        p.setBrush(c);
        p.setPen(Qt::NoPen);
        p.drawPolygon(arrow);
        break;
    }""")

# 5) 选择工具下的命中/拖动
s = s.replace("        if (hit >= 0 && (m_tool == Tool::None || hit == m_selected)) {",
              "        if (hit >= 0 && (m_tool == Tool::None || m_tool == Tool::Select || hit == m_selected)) {")
s = s.replace("    if (m_tool == Tool::None) {\n        m_drag = DragMove;",
              "    if (m_tool == Tool::None || m_tool == Tool::Select) {\n        m_drag = DragMove;")
s = s.replace("        if (hit < 0 && m_tool == Tool::None) m_selected = -1;",
              "        if (hit < 0 && (m_tool == Tool::None || m_tool == Tool::Select)) m_selected = -1;")

# 6) 关键修复：拉框过程中就要实时显示选区（之前 Selecting 阶段只铺暗色遮罩）
old_paint = """    if (m_phase == Selecting || m_sel.isEmpty()) {
        p.fillRect(rect(), QColor(0, 0, 0, 110));
    } else {"""
new_paint = """    if (m_sel.isEmpty()) {
        p.fillRect(rect(), QColor(0, 0, 0, 110));
    } else {"""
if old_paint in s:
    s = s.replace(old_paint, new_paint, 1)

# 7) 拉框过程中只画边框和尺寸，不画手柄（手柄在编辑阶段画）
s = s.replace("""        p.setPen(QPen(Qt::white, 1));
        p.setBrush(QColor("#2f6fed"));
        const int hs = 4;
        QPoint pts[8] = {sel.topLeft(), QPoint(sel.center().x(), sel.top()), sel.topRight(),
                         QPoint(sel.right(), sel.center().y()), sel.bottomRight(),
                         QPoint(sel.center().x(), sel.bottom()), sel.bottomLeft(),
                         QPoint(sel.left(), sel.center().y())};
        for (int i = 0; i < 8; ++i)
            p.drawRect(QRect(pts[i].x() - hs, pts[i].y() - hs, hs * 2, hs * 2));""",
"""        if (m_phase == Editing) {
            p.setPen(QPen(Qt::white, 1));
            p.setBrush(QColor("#2f6fed"));
            const int hs = 4;
            QPoint pts[8] = {sel.topLeft(), QPoint(sel.center().x(), sel.top()), sel.topRight(),
                             QPoint(sel.right(), sel.center().y()), sel.bottomRight(),
                             QPoint(sel.center().x(), sel.bottom()), sel.bottomLeft(),
                             QPoint(sel.left(), sel.center().y())};
            for (int i = 0; i < 8; ++i)
                p.drawRect(QRect(pts[i].x() - hs, pts[i].y() - hs, hs * 2, hs * 2));
        }""")
io.open(p, "w", encoding="utf-8").write(s)
print("overlay updated")
