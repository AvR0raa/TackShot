import io

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\capture.h"
s = io.open(p, encoding="utf-8").read()
if "trimBlackBorder" not in s:
    s = s.replace("QString dpiAwarenessInfo();",
"""QString dpiAwarenessInfo();

// 去掉显示器输出里的黑边（分辨率小于面板、驱动不缩放时会有一圈黑），
// 返回被裁掉的像素数；rectInOut 同步收缩。
QRect trimBlackBorder(QImage& img, QRect rectIn);""")
io.open(p, "w", encoding="utf-8").write(s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\capture.cpp"
s = io.open(p, encoding="utf-8").read()
if "trimBlackBorder" not in s:
    s = s.replace("QRect nativeWindowRect(quintptr id) {",
"""QRect trimBlackBorder(QImage& img, QRect rectIn) {
    if (img.isNull() || img.width() < 64 || img.height() < 64) return rectIn;

    auto rowHasContent = [&img](int y) {
        const QRgb* line = reinterpret_cast<const QRgb*>(img.constScanLine(y));
        for (int x = 0; x < img.width(); x += 3)
            if (qGray(line[x]) > 12) return true;
        return false;
    };
    auto colHasContent = [&img](int x) {
        for (int y = 0; y < img.height(); y += 3)
            if (qGray(img.pixel(x, y)) > 12) return true;
        return false;
    };

    int right = img.width() - 1;
    while (right > img.width() / 2 && !colHasContent(right)) --right;
    int bottom = img.height() - 1;
    while (bottom > img.height() / 2 && !rowHasContent(bottom)) --bottom;
    int left = 0;
    while (left < img.width() / 4 && !colHasContent(left)) ++left;
    int top = 0;
    while (top < img.height() / 4 && !rowHasContent(top)) ++top;

    // 边缘再留 1px，避免把内容切掉
    right = qMin(img.width() - 1, right + 1);
    bottom = qMin(img.height() - 1, bottom + 1);

    QRect trimmed(left, top, right - left + 1, bottom - top + 1);
    if (trimmed.width() < 64 || trimmed.height() < 64) return rectIn;
    // 只有确实存在明显黑边时才裁
    const int lostW = img.width() - trimmed.width();
    const int lostH = img.height() - trimmed.height();
    if (lostW < 24 && lostH < 24) return rectIn;

    img = img.copy(trimmed);
    return QRect(rectIn.topLeft() + QPoint(left, top), trimmed.size());
}

QRect nativeWindowRect(quintptr id) {""")
io.open(p, "w", encoding="utf-8").write(s)

# doCapture：裁剪后同步 rect
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
old = """    {
        QString diag = QString("cursor=%1,%2 screens=")"""
new = """    {
        // 显示器输出若带黑边（分辨率小于面板、驱动不缩放），裁掉后再给覆盖层
        QRect before = rect;
        rect = capture::trimBlackBorder(shot, rect);
        if (rect.size() != before.size())
            captureLog(QString("trim black border: %1x%2 -> %3x%4")
                           .arg(before.width()).arg(before.height())
                           .arg(rect.width()).arg(rect.height()));
    }
    {
        QString diag = QString("cursor=%1,%2 screens=")"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("trim wired into capture")
else:
    print("MISS")
