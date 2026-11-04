import io

# overlay: 工具条配色走主题
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
if '#include "theme.h"' not in s:
    s = s.replace('#include "capture.h"', '#include "capture.h"\n#include "theme.h"')

old_style = s[s.index("    m_bar->setStyleSheet("):s.index("    auto* lay = new QHBoxLayout(m_bar);")]
new_style = r'''    {
        const Palette& t = Theme::p();
        auto rgba = [](const QColor& c) {
            return QString("rgba(%1,%2,%3,%4)").arg(c.red()).arg(c.green())
                .arg(c.blue()).arg(c.alphaF(), 0, 'f', 3);
        };
        m_bar->setStyleSheet(QString(
            "#tsBar { background: %1; border: 1px solid %2; border-radius: 10px; }"
            "#tsBar QToolButton { border: 0; background: transparent; border-radius: 8px; padding: 0; }"
            "#tsBar QToolButton:hover { background: %3; }"
            "#tsBar QToolButton:pressed { background: %4; }"
            "#tsBar QToolButton:checked { background: %5; }"
            "#tsBar QToolButton#tsClose:hover { background: %6; }"
            "#tsBar QToolButton#tsAction { color: %7; font-size: 12px; padding: 0 9px; }"
            "#tsBar QToolButton#tsAction:hover { background: %3; }"
            "#tsBar QLabel { color: %7; font-size: 12px; }")
            .arg(rgba(t.surface), rgba(t.border), rgba(t.hover), rgba(t.pressed),
                 rgba(t.accent), rgba(t.danger), rgba(t.text)));
    }

'''
s = s.replace(old_style, new_style, 1)
# 工具图标颜色
s = s.replace('b->setIcon(makeIcon(t, QColor("#e8eaed")));', 'b->setIcon(makeIcon(t, Theme::p().text));')
s = s.replace('minus->setStyleSheet("QToolButton { color:#e6e8eb; font-size:15px; }");',
              'minus->setStyleSheet(QString("QToolButton { color:%1; font-size:15px; }").arg(Theme::p().text.name()));')
s = s.replace('plus->setStyleSheet("QToolButton { color:#e6e8eb; font-size:15px; }");',
              'plus->setStyleSheet(QString("QToolButton { color:%1; font-size:15px; }").arg(Theme::p().text.name()));')
s = s.replace('p.setPen(QPen(QColor(255, 255, 255, 90), 1));\n        p.setBrush(m_color);',
              'p.setPen(QPen(Theme::p().border, 1));\n        p.setBrush(m_color);')
s = s.replace('p.setPen(QColor("#e8eaed"));\n        p.drawText(tag, Qt::AlignCenter, sizeText);',
              'p.setPen(Theme::p().text);\n        p.drawText(tag, Qt::AlignCenter, sizeText);')
s = s.replace('p.setBrush(QColor(18, 20, 24, 235));', 'p.setBrush(Theme::isDark() ? QColor(18, 20, 24, 235) : QColor(255, 255, 255, 240));')
io.open(p, "w", encoding="utf-8").write(s)

# main.cpp: QKeySequence 构造修正 + 头文件
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("QKeySequence hotkeySeq(Config::get().hotkeyMods, Qt::KeyboardKey(Config::get().hotkeyVk));",
              "QKeySequence hotkeySeq(Qt::Key(Config::get().hotkeyVk), Qt::KeyboardModifiers(Config::get().hotkeyMods));")
s = s.replace("""        actCapture->setShortcut(QKeySequence(Config::get().hotkeyMods,
                                             Qt::KeyboardKey(Config::get().hotkeyVk)));""",
"""        actCapture->setShortcut(QKeySequence(Qt::Key(Config::get().hotkeyVk),
                                             Qt::KeyboardModifiers(Config::get().hotkeyMods)));""")
if "#include <cmath>" not in s:
    s = s.replace('#include <functional>', '#include <functional>\n#include <cmath>\n#include <QPainterPath>')
io.open(p, "w", encoding="utf-8").write(s)
print("theme colors + key sequence fixed")
