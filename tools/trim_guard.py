import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
old = """    {
        // 显示器输出若带黑边（分辨率小于面板、驱动不缩放），裁掉后再给覆盖层
        QRect before = rect;
        rect = capture::trimBlackBorder(shot, rect);
        if (rect.size() != before.size())
            captureLog(QString("trim black border: %1x%2 -> %3x%4")
                           .arg(before.width()).arg(before.height())
                           .arg(rect.width()).arg(rect.height()));
    }
"""
new = """    // 抓屏已经按物理像素取，正常不会有黑边；只有在确实检测到大片纯黑边框时才裁
    {
        QRect before = rect;
        QRect after = capture::trimBlackBorder(shot, rect);
        if (after.size() != before.size() &&
            after.width() >= before.width() * 0.9 && after.height() >= before.height() * 0.9) {
            rect = after;   // 只接受小范围修正，避免误裁黑壁纸
        }
    }
"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("trim made conservative")
else:
    print("MISS")
