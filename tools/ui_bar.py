import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()

# ---------- 1) 图标：2x 渲染 + 统一笔画 ----------
start = s.index("QIcon makeIcon(Tool t, const QColor& c) {")
end = s.index("} // namespace", start)
new_icon = r'''QIcon makeIcon(Tool t, const QColor& c) {
    QIcon icon;
    for (int scale : {1, 2}) {
        QPixmap pm(20 * scale, 20 * scale);
        pm.fill(Qt::transparent);
        pm.setDevicePixelRatio(scale);
        QPainter p(&pm);
        p.setRenderHint(QPainter::Antialiasing, true);
        p.setPen(QPen(c, 1.7, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
        p.setBrush(Qt::NoBrush);
        switch (t) {
        case Tool::Rect:     p.drawRoundedRect(QRectF(3.5, 4.5, 13, 11), 1.5, 1.5); break;
        case Tool::Ellipse:  p.drawEllipse(QRectF(3.5, 4.5, 13, 11)); break;
        case Tool::Arrow:    p.drawLine(QPointF(4, 16), QPointF(15.5, 5.5));
                             p.drawLine(QPointF(15.5, 5.5), QPointF(10, 5.5));
                             p.drawLine(QPointF(15.5, 5.5), QPointF(15.5, 11)); break;
        case Tool::Line:     p.drawLine(QPointF(4, 16), QPointF(16, 4)); break;
        case Tool::Pen:      { QPainterPath path;
                               path.moveTo(4, 14.5);
                               path.cubicTo(7, 6, 10, 17, 16, 6);
                               p.drawPath(path); break; }
        case Tool::Highlight: { QPen hp(c, 4.5, Qt::SolidLine, Qt::RoundCap);
                                p.setPen(hp);
                                p.drawLine(QPointF(5, 15), QPointF(15, 7)); break; }
        case Tool::Mosaic:   for (int i = 0; i < 3; ++i) for (int j = 0; j < 3; ++j) {
                                 QColor cc = ((i + j) % 2) ? c : c.darker(160);
                                 p.fillRect(QRectF(4.5 + i * 4, 5.5 + j * 4, 3.2, 3.2), cc);
                             }
                             break;
        case Tool::Text:     { QFont f; f.setBold(true); f.setPixelSize(14); p.setFont(f);
                               p.drawText(QRectF(1, 1, 18, 18), Qt::AlignCenter, "T"); break; }
        case Tool::Number:   p.drawEllipse(QRectF(3.5, 3.5, 13, 13)); break;
        case Tool::Select: {
            QPolygonF arrow;
            arrow << QPointF(5.5, 3.5) << QPointF(5.5, 16) << QPointF(9, 12.4)
                  << QPointF(11.6, 17.5) << QPointF(14, 16.3) << QPointF(11.4, 11.4)
                  << QPointF(16.3, 10.6);
            p.setBrush(c);
            p.setPen(Qt::NoPen);
            p.drawPolygon(arrow);
            break;
        }
        default: break;
        }
        p.end();
        icon.addPixmap(pm);
    }
    return icon;
}

'''
s = s[:start] + new_icon + s[end:]

# ---------- 2) 工具条重写 ----------
start = s.index("void Overlay::buildToolbar() {")
end = s.index("QRectF Overlay::annotBounds(const Annotation& a) const {")
new_bar = r'''void Overlay::buildToolbar() {
    m_bar = new QWidget(this);
    m_bar->setObjectName(QStringLiteral("tsBar"));
    m_bar->setAttribute(Qt::WA_StyledBackground, true);
    m_bar->setStyleSheet(
        "#tsBar { background: rgba(30,32,36,0.97);"
        "         border: 1px solid rgba(255,255,255,0.10); border-radius: 10px; }"
        "#tsBar QToolButton { border: 0; background: transparent; border-radius: 8px; padding: 0; }"
        "#tsBar QToolButton:hover { background: rgba(255,255,255,0.10); }"
        "#tsBar QToolButton:pressed { background: rgba(255,255,255,0.18); }"
        "#tsBar QToolButton:checked { background: #2f6fed; }"
        "#tsBar QToolButton#tsClose:hover { background: rgba(255,69,58,0.85); }"
        "#tsBar QToolButton#tsAction { color: #e6e8eb; font-size: 12px; padding: 0 9px; }"
        "#tsBar QToolButton#tsAction:hover { background: rgba(255,255,255,0.12); }"
        "#tsBar QLabel { color: #e6e8eb; font-size: 12px; }");

    auto* lay = new QHBoxLayout(m_bar);
    lay->setContentsMargins(8, 6, 8, 6);
    lay->setSpacing(3);

    auto addSep = [&]() {
        auto* line = new QFrame(m_bar);
        line->setFrameShape(QFrame::VLine);
        line->setStyleSheet("color: rgba(255,255,255,0.12);");
        line->setFixedHeight(20);
        lay->addSpacing(3);
        lay->addWidget(line);
        lay->addSpacing(3);
    };

    const QVector<Tool> tools = {Tool::Select, Tool::Rect, Tool::Ellipse, Tool::Arrow, Tool::Line,
                                 Tool::Pen, Tool::Highlight, Tool::Mosaic, Tool::Text, Tool::Number};
    const QStringList tips = {QStringLiteral("选择 / 移动标注"),
                              QStringLiteral("矩形"), QStringLiteral("椭圆"),
                              QStringLiteral("箭头"), QStringLiteral("直线"),
                              QStringLiteral("画笔"), QStringLiteral("荧光笔"),
                              QStringLiteral("马赛克"), QStringLiteral("文字"),
                              QStringLiteral("序号")};
    for (int i = 0; i < tools.size(); ++i) {
        Tool t = tools[i];
        auto* b = new QToolButton(m_bar);
        b->setIcon(makeIcon(t, QColor("#e8eaed")));
        b->setIconSize(QSize(20, 20));
        b->setFixedSize(32, 32);
        b->setCheckable(true);
        b->setAutoRaise(true);
        b->setCursor(Qt::PointingHandCursor);
        b->setToolTip(tips.value(i));
        connect(b, &QToolButton::clicked, this, [this, t]() { onToolClicked(t); });
        lay->addWidget(b);
        m_toolButtons.append(b);
    }

    addSep();

    // 颜色
    m_colorBtn = new QToolButton(m_bar);
    m_colorBtn->setFixedSize(28, 28);
    m_colorBtn->setToolTip(QStringLiteral("颜色"));
    m_colorBtn->setCursor(Qt::PointingHandCursor);
    connect(m_colorBtn, &QToolButton::clicked, this, &Overlay::onPickColor);
    lay->addWidget(m_colorBtn);

    // 粗细：− 数值 + 预览
    auto* minus = new QToolButton(m_bar);
    minus->setText(QStringLiteral("−"));
    minus->setFixedSize(24, 28);
    minus->setStyleSheet("QToolButton { color:#e6e8eb; font-size:15px; }");
    minus->setToolTip(QStringLiteral("变细"));
    connect(minus, &QToolButton::clicked, this, [this]() { setWidth(int(m_width) - 1); });
    lay->addWidget(minus);

    m_widthLabel = new QLabel(QString::number(int(m_width)), m_bar);
    m_widthLabel->setFixedWidth(16);
    m_widthLabel->setAlignment(Qt::AlignCenter);
    lay->addWidget(m_widthLabel);

    auto* plus = new QToolButton(m_bar);
    plus->setText(QStringLiteral("+"));
    plus->setFixedSize(24, 28);
    plus->setStyleSheet("QToolButton { color:#e6e8eb; font-size:15px; }");
    plus->setToolTip(QStringLiteral("变粗"));
    connect(plus, &QToolButton::clicked, this, [this]() { setWidth(int(m_width) + 1); });
    lay->addWidget(plus);

    m_widthPreview = new QLabel(m_bar);
    m_widthPreview->setFixedSize(34, 28);
    m_widthPreview->setToolTip(QStringLiteral("当前笔画粗细"));
    lay->addWidget(m_widthPreview);

    addSep();

    auto addAction = [&](const QString& text, const QString& tip, auto fn, const char* name = "tsAction") {
        auto* b = new QToolButton(m_bar);
        b->setObjectName(QString::fromLatin1(name));
        b->setText(text);
        b->setToolTip(tip);
        b->setAutoRaise(true);
        b->setCursor(Qt::PointingHandCursor);
        b->setFixedHeight(30);
        b->setMinimumWidth(46);
        connect(b, &QToolButton::clicked, this, fn);
        lay->addWidget(b);
        return b;
    };

    addAction(QStringLiteral("识别"), QStringLiteral("本地 OCR 文字识别"), [this]() { onOcr(); });
    addAction(QStringLiteral("长图"), QStringLiteral("长截图（滚动拼接）"), [this]() { onLongShot(); });
    addAction(QStringLiteral("录制"), QStringLiteral("录制 GIF / MP4"), [this]() { onRecord(); });
    addSep();
    addAction(QStringLiteral("撤销"), QStringLiteral("撤销 (Ctrl+Z)"), [this]() { onUndo(); });
    addAction(QStringLiteral("重做"), QStringLiteral("重做 (Ctrl+Shift+Z)"), [this]() { onRedo(); });
    addSep();
    addAction(QStringLiteral("复制"), QStringLiteral("复制到剪贴板 (Enter)"), [this]() { onCopy(); });
    addAction(QStringLiteral("保存"), QStringLiteral("保存到文件 (Ctrl+S)"), [this]() { onSave(); });
    addAction(QStringLiteral("贴图"), QStringLiteral("钉在屏幕上"), [this]() { onPin(); });
    addAction(QStringLiteral("关闭"), QStringLiteral("取消 (Esc)"), [this]() { onClose(); }, "tsClose");

    // 阴影
    auto* shadow = new QGraphicsDropShadowEffect(m_bar);
    shadow->setBlurRadius(24);
    shadow->setOffset(0, 6);
    shadow->setColor(QColor(0, 0, 0, 160));
    m_bar->setGraphicsEffect(shadow);

    m_bar->hide();
    updateToolButtons();
    layout()->activate();
}

void Overlay::placeToolbar() {
    if (!m_bar) return;
    m_bar->adjustSize();
    QRect sel = selRectWidget();
    QSize s = m_bar->sizeHint();
    int x = sel.right() - s.width();
    int y = sel.bottom() + 10;
    if (y + s.height() > height() - 6) y = sel.top() - s.height() - 10;
    if (y < 6) y = qBound(6, sel.center().y() - s.height() / 2, qMax(6, height() - s.height() - 6));
    x = qBound(6, x, qMax(6, width() - s.width() - 6));
    m_bar->setGeometry(x, y, s.width(), s.height());
    m_bar->show();
    m_bar->raise();
}

void Overlay::setWidth(int w) {
    w = qBound(1, w, 24);
    m_width = w;
    Config::get().penWidth = w;
    if (m_widthLabel) m_widthLabel->setText(QString::number(w));
    if (m_widthPreview) {
        QPixmap pm(34, 28);
        pm.fill(Qt::transparent);
        QPainter pp(&pm);
        pp.setRenderHint(QPainter::Antialiasing, true);
        pp.setPen(QPen(m_color, w, Qt::SolidLine, Qt::RoundCap));
        pp.drawLine(QPointF(4, 14), QPointF(30, 14));
        pp.end();
        m_widthPreview->setPixmap(pm);
    }
    update();
}

void Overlay::updateToolButtons() {
    const QVector<Tool> order = {Tool::Select, Tool::Rect, Tool::Ellipse, Tool::Arrow, Tool::Line,
                                 Tool::Pen, Tool::Highlight, Tool::Mosaic, Tool::Text, Tool::Number};
    for (int i = 0; i < m_toolButtons.size() && i < order.size(); ++i)
        m_toolButtons[i]->setChecked(order[i] == m_tool);
    if (m_colorBtn) {
        QPixmap pm(52, 52);
        pm.fill(Qt::transparent);
        pm.setDevicePixelRatio(2);
        QPainter p(&pm);
        p.setRenderHint(QPainter::Antialiasing, true);
        p.setPen(QPen(QColor(255, 255, 255, 90), 1));
        p.setBrush(m_color);
        p.drawRoundedRect(QRectF(2, 2, 22, 22), 5, 5);
        p.end();
        m_colorBtn->setIcon(QIcon(pm));
        m_colorBtn->setIconSize(QSize(24, 24));
    }
    setWidth(int(m_width));
}

'''
s = s[:start] + new_bar + s[end:]
s = s.replace('#include <QVariantAnimation>', '#include <QVariantAnimation>\n#include <QGraphicsDropShadowEffect>\n#include <QFrame>')
io.open(p, "w", encoding="utf-8").write(s)

# 头文件：宽度预览控件
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.h"
s = io.open(p, encoding="utf-8").read()
if "m_widthPreview" not in s:
    s = s.replace("    QLabel*     m_widthLabel = nullptr;",
                  "    QLabel*     m_widthLabel = nullptr;\n    QLabel*     m_widthPreview = nullptr;")
io.open(p, "w", encoding="utf-8").write(s)
print("toolbar redesigned")
