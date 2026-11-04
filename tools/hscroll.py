import io

# longshot.h：加入方向参数
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\longshot.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("""namespace longshot {

QImage appendFrame(const QImage& canvas, const QImage& frame, bool* matched = nullptr);

} // namespace longshot""",
"""namespace longshot {

// 竖向：新内容出现在下方
QImage appendFrame(const QImage& canvas, const QImage& frame, bool* matched = nullptr);

// 横向：新内容出现在右侧（内部用转置复用竖向逻辑）
QImage appendFrameH(const QImage& canvas, const QImage& frame, bool* matched = nullptr);

// 自动判断方向：返回图，dir 输出 0=竖向 1=横向
QImage appendAuto(const QImage& canvas, const QImage& frame, int* dir, bool* matched);

} // namespace longshot""")
io.open(p, "w", encoding="utf-8").write(s)

# longshot.cpp：追加实现
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\longshot.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("} // namespace longshot", """
QImage appendFrameH(const QImage& canvas, const QImage& frame, bool* matched) {
    if (frame.isNull()) return canvas;
    if (canvas.isNull()) return frame;
    QImage c = canvas.transposed();
    QImage f = frame.transposed();
    QImage r = appendFrame(c, f, matched);
    return r.transposed();
}

QImage appendAuto(const QImage& canvas, const QImage& frame, int* dir, bool* matched) {
    if (dir) *dir = 0;
    if (canvas.isNull() || frame.isNull()) {
        if (matched) *matched = false;
        return canvas.isNull() ? frame : canvas;
    }
    // 两种方向都试，选“重叠更大”的那个
    bool mv = false, mh = false;
    QImage rv = appendFrame(canvas, frame, &mv);
    QImage rh = appendFrameH(canvas, frame, &mh);
    if (mv && !mh) { if (dir) *dir = 0; if (matched) *matched = true; return rv; }
    if (mh && !mv) { if (dir) *dir = 1; if (matched) *matched = true; return rh; }
    if (mv && mh) {
        // 都成立时，取新增面积更小的（更可能是真实方向）
        int addV = rv.width() * (rv.height() - canvas.height());
        int addH = (rh.width() - canvas.width()) * rh.height();
        if (addV <= addH) { if (dir) *dir = 0; if (matched) *matched = true; return rv; }
        if (dir) *dir = 1; if (matched) *matched = true; return rh;
    }
    if (matched) *matched = false;
    return canvas;
}

} // namespace longshot""")
io.open(p, "w", encoding="utf-8").write(s)
print("longshot generalized")

# LongShotBar：改用 appendAuto
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\sessions.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("""        bool matched = false;
        QImage next = longshot::appendFrame(m_canvas, frame, &matched);
        if (matched) {
            m_canvas = next;
            m_frames++;
        }""",
"""        bool matched = false;
        int dir = 0;
        QImage next = longshot::appendAuto(m_canvas, frame, &dir, &matched);
        if (matched) {
            m_canvas = next;
            m_dir = dir;
            m_frames++;
        }""")
s = s.replace('m_info->setText(QStringLiteral("长截图：已拼接 %1 段，高度 %2 px")\n                        .arg(m_frames + 1).arg(m_canvas.height()));',
              'm_info->setText(QStringLiteral("长截图：已拼接 %1 段（%2） %3 x %4 px")\n                        .arg(m_frames + 1).arg(m_dir ? QStringLiteral("横向") : QStringLiteral("竖向"))\n                        .arg(m_canvas.width()).arg(m_canvas.height()));')
io.open(p, "w", encoding="utf-8").write(s)

# sessions.h：加 m_dir
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\sessions.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    int m_frames = 0;\n};", "    int m_frames = 0;\n    int m_dir = 0;\n};")
io.open(p, "w", encoding="utf-8").write(s)
print("sessions updated")
