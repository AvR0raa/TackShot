import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
old = """    // 1) 把窗口明确绑到目标屏
    if (m_targetScreen) {
        if (QWindow* h = windowHandle()) {
            if (h->screen() != m_targetScreen) h->setScreen(m_targetScreen);
        }
    }"""
new = """    // 1) 把窗口明确绑到目标屏；如果创建时落在了别的屏，surface 的 DPR 会是错的，
    //    必须重建一次（否则 125% 屏上的窗口只会画出 80% 的内容）。
    if (m_targetScreen) {
        if (QWindow* h = windowHandle()) {
            if (h->screen() != m_targetScreen) {
                h->setScreen(m_targetScreen);
                if (!m_rebuilding) {
                    m_rebuilding = true;
                    QTimer::singleShot(0, this, [this]() {
                        m_rebuilding = false;
                        hide();
                        show();
                    });
                }
            }
        }
    }"""
if old in s:
    s = s.replace(old, new, 1)
    s = s.replace('#include <QWindow>', '#include <QWindow>\n#include <QTimer>')
    io.open(p, "w", encoding="utf-8").write(s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.h"
s = io.open(p, encoding="utf-8").read()
if "m_rebuilding" not in s:
    s = s.replace("    QScreen* m_targetScreen = nullptr;",
                  "    QScreen* m_targetScreen = nullptr;\n    bool m_rebuilding = false;")
io.open(p, "w", encoding="utf-8").write(s)
print("surface rebuild on screen change")
