import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
old = """    // 淡入，避免“啪”地一下出现
    setWindowOpacity(0.0);
    auto* fade = new QPropertyAnimation(this, "windowOpacity", this);
    fade->setDuration(110);
    fade->setStartValue(0.0);
    fade->setEndValue(1.0);
    fade->setEasingCurve(QEasingCurve::OutCubic);
    fade->start(QAbstractAnimation::DeleteWhenStopped);"""
new = """    // 注意：不要用 setWindowOpacity 做淡入——在部分机器上会让窗口 surface 按 1.0 的
    // 缩放创建，结果 125% 屏上只画出 80% 的内容（右下留黑）。
    setWindowOpacity(1.0);"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("fade disabled")
else:
    print("MISS")
