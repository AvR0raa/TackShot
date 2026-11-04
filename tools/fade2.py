import io

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.h"
s = io.open(p, encoding="utf-8").read()
if "m_fade" not in s:
    s = s.replace("    bool m_rebuilding = false;", "    bool m_rebuilding = false;\n    qreal m_fade = 1.0;   // 遮罩淡入进度（不动窗口透明度，避免 surface 缩放问题）")
io.open(p, "w", encoding="utf-8").write(s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("""    // 注意：不要用 setWindowOpacity 做淡入——在部分机器上会让窗口 surface 按 1.0 的
    // 缩放创建，结果 125% 屏上只画出 80% 的内容（右下留黑）。
    setWindowOpacity(1.0);""",
"""    // 淡入只做在“遮罩透明度”上：不动窗口 opacity，
    // 因为 setWindowOpacity 在部分机器上会让 surface 按 1.0 缩放创建（125% 屏只画 80%）。
    setWindowOpacity(1.0);
    m_fade = 0.0;
    {
        auto* anim = new QVariantAnimation(this);
        anim->setStartValue(0.0);
        anim->setEndValue(1.0);
        anim->setDuration(130);
        anim->setEasingCurve(QEasingCurve::OutCubic);
        connect(anim, &QVariantAnimation::valueChanged, this, [this](const QVariant& v) {
            m_fade = v.toReal();
            update();
        });
        anim->start(QAbstractAnimation::DeleteWhenStopped);
    }""")
s = s.replace("p.fillRect(rect(), QColor(0, 0, 0, 110));",
              "p.fillRect(rect(), QColor(0, 0, 0, int(110 * m_fade)));")
s = s.replace("for (const QRect& r : outside) p.fillRect(r, QColor(0, 0, 0, 110));",
              "for (const QRect& r : outside) p.fillRect(r, QColor(0, 0, 0, int(110 * m_fade)));")
s = s.replace('#include <QTimer>', '#include <QTimer>\n#include <QVariantAnimation>')
io.open(p, "w", encoding="utf-8").write(s)
print("paint-level fade added")
