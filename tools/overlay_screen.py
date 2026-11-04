import io

# ---------- overlay.h：记录目标屏幕 ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("class QLabel;", "class QLabel;\nclass QScreen;")
s = s.replace("    void demoSelect(const QRect& sel)",
              "    void setTargetScreen(QScreen* s) { m_targetScreen = s; }\n    void demoSelect(const QRect& sel)")
s = s.replace("    QImage m_shot;", "    QScreen* m_targetScreen = nullptr;\n    QImage m_shot;")
s = s.replace("    void paintEvent(QPaintEvent*) override;",
              "    void paintEvent(QPaintEvent*) override;\n    void showEvent(QShowEvent*) override;")
io.open(p, "w", encoding="utf-8").write(s)

# ---------- overlay.cpp ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("void Overlay::paintEvent(QPaintEvent*) {",
"""void Overlay::showEvent(QShowEvent* e) {
    QWidget::showEvent(e);
    // 明确把窗口绑到目标屏，避免 Qt 按创建位置猜错屏幕导致 DPR 不对
    if (m_targetScreen) {
        if (QWindow* h = windowHandle()) {
            if (h->screen() != m_targetScreen) h->setScreen(m_targetScreen);
        }
    }
    if (m_targetScreen) {
        QFile lf(Config::get().dataDir() + "/capture.log");
        if (lf.open(QIODevice::Append)) {
            lf.write(QString("[%1] overlay win=%2,%3 %4x%5 dpr=%6 screen=%7 screenDpr=%8\\n")
                         .arg(QDateTime::currentDateTime().toString("MM-dd HH:mm:ss"))
                         .arg(x()).arg(y()).arg(width()).arg(height())
                         .arg(devicePixelRatioF())
                         .arg(m_targetScreen->name())
                         .arg(m_targetScreen->devicePixelRatio())
                         .toUtf8());
            lf.close();
        }
    }
}

void Overlay::paintEvent(QPaintEvent*) {""")
s = s.replace("#include <QPropertyAnimation>", "#include <QPropertyAnimation>\n#include <QWindow>\n#include <QScreen>\n#include <QDateTime>\n#include <QFile>")
io.open(p, "w", encoding="utf-8").write(s)

# ---------- main.cpp：把目标屏传进去 ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("static void showOverlay(const QImage& shot, const QRect& rect, qreal dpr) {\n    if (g_overlay) { g_overlay->close(); g_overlay = nullptr; }\n    g_overlay = new Overlay(shot, rect, dpr);",
"""static void showOverlay(const QImage& shot, const QRect& rect, qreal dpr) {
    if (g_overlay) { g_overlay->close(); g_overlay = nullptr; }
    g_overlay = new Overlay(shot, rect, dpr);
    if (QScreen* sc = QGuiApplication::screenAt(QPoint(int(rect.center().x() / dpr),
                                                       int(rect.center().y() / dpr))))
        g_overlay->setTargetScreen(sc);""")
io.open(p, "w", encoding="utf-8").write(s)
print("overlay screen binding + logging added")
