import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
old = """        info += "dpi: " + capture::dpiAwarenessInfo() + "\\n";"""
new = """        if (!img.isNull()) {
            // 对左半屏做去黑边测试
            QImage leftHalf = img.copy(QRect(0, 0, img.width() / 2, img.height()));
            QRect before(0, 0, leftHalf.width(), leftHalf.height());
            QRect after = capture::trimBlackBorder(leftHalf, before);
            info += QString("leftHalf before=%1x%2 after=%3x%4\\n")
                        .arg(before.width()).arg(before.height())
                        .arg(after.width()).arg(after.height());
            leftHalf.save(outPng + ".left.png");
        }
        info += "dpi: " + capture::dpiAwarenessInfo() + "\\n";"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("snap trim test added")
else:
    print("MISS")
