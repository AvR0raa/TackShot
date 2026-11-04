import io

# ---------------- longshot.h ----------------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\longshot.h"
s = io.open(p, encoding="utf-8").read()
if "verticalShift" not in s:
    s = s.replace("// 自动判断方向：返回图，dir 输出 0=竖向 1=横向",
"""// 估算 cur 相对 prev 的竖向位移（像素）：
//   > 0  内容上移（向下滚动），值即滚动距离
//   <= 0 内容下移（向上回滚）或几乎没动
//   INT_MIN 表示无法判断（尺寸不一致 / 找不到匹配）
int verticalShift(const QImage& prev, const QImage& cur);

// 自动判断方向：返回图，dir 输出 0=竖向 1=横向""")
io.open(p, "w", encoding="utf-8").write(s)

# ---------------- longshot.cpp ----------------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\longshot.cpp"
s = io.open(p, encoding="utf-8").read()
if "verticalShift" not in s:
    s = s.replace("QImage appendFrameH(const QImage& canvas, const QImage& frame, bool* matched) {",
r'''int verticalShift(const QImage& prev, const QImage& cur) {
    if (prev.isNull() || cur.isNull() || prev.width() != cur.width()) return INT_MIN;

    const int TW = 240;
    int ph = 0, chh = 0;
    QVector<quint8> pg = grayStrip(prev, TW, &ph);
    QVector<quint8> cg = grayStrip(cur, TW, &chh);

    int th = std::max(16, std::min(ph / 4, 40));
    if (ph <= th || chh <= th) return INT_MIN;

    const int maxShift = std::min(ph - th, 600);
    int best = INT_MIN;
    double bestScore = 1e18;

    for (int dy = -maxShift; dy <= maxShift; ++dy) {
        int startP = dy >= 0 ? dy : 0;
        int startC = dy >= 0 ? 0 : -dy;
        if (startP + th > ph || startC + th > chh) continue;

        double sad = 0;
        for (int r = 0; r < th; r += 4) {
            const quint8* a = pg.constData() + (startP + r) * TW;
            const quint8* b = cg.constData() + (startC + r) * TW;
            for (int x = 0; x < TW; ++x) sad += std::abs(int(a[x]) - int(b[x]));
        }
        if (sad < bestScore) { bestScore = sad; best = dy; }
    }

    const int samples = (th / 4 + 1) * TW;
    if (bestScore / std::max(1, samples) > 8.0) return INT_MIN;
    return best;
}

QImage appendFrameH(const QImage& canvas, const QImage& frame, bool* matched) {''')
io.open(p, "w", encoding="utf-8").write(s)

# ---------------- sessions.cpp ----------------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\sessions.cpp"
s = io.open(p, encoding="utf-8").read()
old = """        bool matched = false;
        int dir = 0;
        QImage next = longshot::appendAuto(m_canvas, frame, &dir, &matched);
        if (matched) {
            m_canvas = next;
            m_dir = dir;
            m_frames++;
        }
        m_prev = frame;"""
new = """        // 长截图固定竖向拼接；先判断滚动方向，回滚（向上滚）的帧直接丢弃，
        // 否则会把已经拍过的内容再拼一遍。
        const int dy = longshot::verticalShift(m_prev, frame);
        bool skip = false;
        if (dy != INT_MIN && dy <= 1) {
            skip = true;                      // 回滚或没滚动
            m_rolledBack += (dy != INT_MIN && dy < -1) ? 1 : 0;
        }
        if (!skip) {
            bool matched = false;
            QImage next = longshot::appendFrame(m_canvas, frame, &matched);
            if (matched) {
                m_canvas = next;
                m_dir = 0;                    // 竖向
                m_frames++;
            }
        }
        m_prev = frame;"""
if old in s:
    s = s.replace(old, new, 1)
    s = s.replace("""    m_info->setText(QStringLiteral("长截图：已拼接 %1 段（%2） %3 x %4 px")
                        .arg(m_frames + 1).arg(m_dir ? QStringLiteral("横向") : QStringLiteral("竖向"))
                        .arg(m_canvas.width()).arg(m_canvas.height()));""",
"""    QString info = QStringLiteral("长截图：已拼接 %1 段（竖向） %2 x %3 px")
                       .arg(m_frames + 1).arg(m_canvas.width()).arg(m_canvas.height());
    if (m_rolledBack > 0)
        info += QStringLiteral(" · 已忽略 %1 次回滚").arg(m_rolledBack);
    m_info->setText(info);""")
    io.open(p, "w", encoding="utf-8").write(s)

# sessions.h：加 m_rolledBack
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\sessions.h"
s = io.open(p, encoding="utf-8").read()
if "m_rolledBack" not in s:
    s = s.replace("    int m_frames = 0;", "    int m_frames = 0;\n    int m_rolledBack = 0;")
    io.open(p, "w", encoding="utf-8").write(s)
print("longshot: vertical + rollback guard applied")
