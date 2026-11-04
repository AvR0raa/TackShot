import io

# ---------- theme.cpp：勾选框图标 + 导航栏配色 ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\theme.cpp"
s = io.open(p, encoding="utf-8").read()

s = s.replace('#include <QStyleHints>', '#include <QStyleHints>\n#include <QDir>\n#include <QPainter>\n#include <QPainterPath>\n#include <QPixmap>')

s = s.replace("QString Theme::styleSheet() {\n    const Palette& c = p();",
"""static QString ensureCheckPixmap() {
    const Palette& c = Theme::p();
    QString dir = Config::get().dataDir() + "/theme";
    QDir().mkpath(dir);
    QString path = dir + QString("/check_%1.png").arg(c.dark ? "dark" : "light");
    QPixmap pm(30, 30);
    pm.fill(Qt::transparent);
    QPainter p(&pm);
    p.setRenderHint(QPainter::Antialiasing, true);
    p.setPen(Qt::NoPen);
    p.setBrush(c.accent);
    p.drawRoundedRect(QRectF(1, 1, 28, 28), 7, 7);
    QPainterPath check;
    check.moveTo(8, 15.5);
    check.lineTo(13, 20.5);
    check.lineTo(22, 9.5);
    p.setBrush(Qt::NoBrush);
    p.setPen(QPen(c.accentText, 2.4, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
    p.drawPath(check);
    p.end();
    if (pm.save(path)) return path;
    return QString();
}

QString Theme::styleSheet() {
    const Palette& c = p();
    const QString checkPath = ensureCheckPixmap();""")

s = s.replace('''        "QCheckBox::indicator:checked { background: %6; border-color: %6; }"''',
'''        + (checkPath.isEmpty() ? QString("QCheckBox::indicator:checked { background: %1; border-color: %1; }").arg(rgba(c.accent))
                               : QString("QCheckBox::indicator:checked { image: url(\\"%1\\"); border: 0; background: transparent; }").arg(checkPath))
        + "QListWidget#tsNav { background: %12; border-right: 1px solid %5; }"''')

s = s.replace(".arg(rgba(c.windowBg), rgba(c.text), rgba(c.subText), rgba(c.surfaceAlt),\n             rgba(c.border), rgba(c.accent), rgba(c.accentText), rgba(c.surface),\n             rgba(c.hover), rgba(c.pressed), rgba(c.surfaceAlt));",
".arg(rgba(c.windowBg), rgba(c.text), rgba(c.subText), rgba(c.surfaceAlt),\n             rgba(c.border), rgba(c.accent), rgba(c.accentText), rgba(c.surface),\n             rgba(c.hover), rgba(c.pressed), rgba(c.surfaceAlt), rgba(c.windowBg));")
io.open(p, "w", encoding="utf-8").write(s)

# ---------- settingsdialog.cpp：给导航栏一个 objectName ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    m_nav->setFixedWidth(158);", "    m_nav->setObjectName(QStringLiteral(\"tsNav\"));\n    m_nav->setFixedWidth(158);")
io.open(p, "w", encoding="utf-8").write(s)

# ---------- pinwindow.cpp：动画兜底 ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\pinwindow.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    anim->start(QAbstractAnimation::DeleteWhenStopped);\n}",
"""    anim->start(QAbstractAnimation::DeleteWhenStopped);

    // 兜底：若动画因任何原因没跑起来，200ms 后强制显示完
    QTimer::singleShot(200, this, [this]() {
        if (m_reveal < 1.0) { m_reveal = 1.0; update(); }
    });
}""")
io.open(p, "w", encoding="utf-8").write(s)

# ---------- main.cpp：预览时把事件泵起来 ----------
p = r"C:\Users\laiki\\.dsh\\workspace\\tackshot\\src\\main.cpp".replace("\\\\", "\\")
s = io.open(p, encoding="utf-8").read()
s = s.replace("""            pin->show();
            QCoreApplication::processEvents();
            QThread::msleep(250);
            QCoreApplication::processEvents();""",
"""            pin->show();
            for (int i = 0; i < 12; ++i) {
                QCoreApplication::processEvents();
                QThread::msleep(30);
            }""")
io.open(p, "w", encoding="utf-8").write(s)
print("checkbox + nav + pin fallback applied")
