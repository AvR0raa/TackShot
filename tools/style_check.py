import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\theme.cpp"
s = io.open(p, encoding="utf-8").read()

# 用 QProxyStyle 画勾选框，替代 QSS 图片
s = s.replace('#include <QStyleHints>', '#include <QStyleHints>\n#include <QProxyStyle>\n#include <QStyleOption>\n#include <QPainterPath>')

s = s.replace("static QString ensureCheckPixmap() {",
"""class TsStyle : public QProxyStyle {
public:
    void drawPrimitive(PrimitiveElement pe, const QStyleOption* opt, QPainter* p,
                       const QWidget* w) const override {
        if (pe == PE_IndicatorCheckBox && opt && p) {
            const Palette& c = Theme::p();
            const bool on = (opt->state & State_On) != 0;
            const bool hover = (opt->state & State_MouseOver) != 0;
            const bool disabled = (opt->state & State_Enabled) == 0;
            QRectF r = QRectF(opt->rect).adjusted(0.5, 0.5, -0.5, -0.5);
            p->save();
            p->setRenderHint(QPainter::Antialiasing, true);
            QColor fill = on ? c.accent : (hover ? c.hover : c.surfaceAlt);
            QColor line = on ? c.accent : c.border;
            if (disabled) { fill.setAlpha(90); line.setAlpha(90); }
            p->setPen(QPen(line, 1.2));
            p->setBrush(fill);
            p->drawRoundedRect(r, 3.5, 3.5);
            if (on) {
                QPainterPath path;
                path.moveTo(r.left() + r.width() * 0.24, r.top() + r.height() * 0.52);
                path.lineTo(r.left() + r.width() * 0.44, r.top() + r.height() * 0.72);
                path.lineTo(r.left() + r.width() * 0.78, r.top() + r.height() * 0.28);
                QColor tick = c.accentText;
                if (disabled) tick.setAlpha(120);
                p->setPen(QPen(tick, 1.9, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
                p->setBrush(Qt::NoBrush);
                p->drawPath(path);
            }
            p->restore();
            return;
        }
        QProxyStyle::drawPrimitive(pe, opt, p, w);
    }
};

static QString ensureCheckPixmap() {""")

# 去掉 QSS 里的 indicator 背景/图片规则，只留尺寸
s = s.replace('''        "QCheckBox::indicator { width: 15px; height: 15px; border-radius: 3px;"
        "  border: 1px solid %5; background: %4; }"''',
'''        "QCheckBox::indicator { width: 15px; height: 15px; }"''')
s = s.replace('''        + (checkPath.isEmpty() ? QString("QCheckBox::indicator:checked { background: %1; border-color: %1; }").arg(rgba(c.accent))
                               : QString("QCheckBox::indicator:checked { image: url(\\"%1\\"); border: 0; background: transparent; }").arg(checkPath))
        + "QListWidget#tsNav { background: %12; border-right: 1px solid %5; }"''',
'''        "QListWidget#tsNav { background: %12; border-right: 1px solid %5; }"''')

# 安装样式
s = s.replace("void Theme::applyGlobal() {\n    if (qApp) qApp->setStyleSheet(styleSheet());\n}",
"""void Theme::applyGlobal() {
    if (!qApp) return;
    static bool styleInstalled = false;
    if (!styleInstalled) {
        qApp->setStyle(new TsStyle);
        styleInstalled = true;
    }
    qApp->setStyleSheet(styleSheet());
}""")
io.open(p, "w", encoding="utf-8").write(s)
print("checkbox drawn via proxy style")
