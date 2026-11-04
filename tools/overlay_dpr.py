import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()

old = """void Overlay::showEvent(QShowEvent* e) {
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
}"""

new = """void Overlay::showEvent(QShowEvent* e) {
    QWidget::showEvent(e);

    // 1) 把窗口明确绑到目标屏
    if (m_targetScreen) {
        if (QWindow* h = windowHandle()) {
            if (h->screen() != m_targetScreen) h->setScreen(m_targetScreen);
        }
    }

    // 2) 用窗口实际的 DPR 校正几何与坐标换算。
    //    某些情况下 Qt 会给覆盖层 1.0 的 DPR，导致 2048x1152 的窗口只铺满 2560x1440 屏幕的 80%。
    qreal actual = m_scale;
    if (QWindow* h = windowHandle()) actual = h->devicePixelRatio();
    if (actual > 0.1 && qAbs(actual - m_scale) > 0.01) {
        m_scale = actual;
        QRect g(QPoint(qRound(m_physRect.x() / actual), qRound(m_physRect.y() / actual)),
                QSize(qRound(m_physRect.width() / actual), qRound(m_physRect.height() / actual)));
        setGeometry(g);
        updateToolButtons();
        if (m_bar && m_bar->isVisible()) placeToolbar();
        update();
    }

    if (m_targetScreen) {
        QFile lf(Config::get().dataDir() + "/capture.log");
        if (lf.open(QIODevice::Append)) {
            lf.write(QString("[%1] overlay win=%2,%3 %4x%5 scale=%6 winDpr=%7 screen=%8 screenDpr=%9 "
                             "QT_SCALE_FACTOR=%10 QT_ENABLE_HIGHDPI_SCALING=%11\\n")
                         .arg(QDateTime::currentDateTime().toString("MM-dd HH:mm:ss"))
                         .arg(x()).arg(y()).arg(width()).arg(height())
                         .arg(m_scale)
                         .arg(windowHandle() ? windowHandle()->devicePixelRatio() : -1.0)
                         .arg(m_targetScreen->name())
                         .arg(m_targetScreen->devicePixelRatio())
                         .arg(qEnvironmentVariable("QT_SCALE_FACTOR", "-"))
                         .arg(qEnvironmentVariable("QT_ENABLE_HIGHDPI_SCALING", "-"))
                         .toUtf8());
            lf.close();
        }
    }
}"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("overlay DPR self-correction added")
else:
    print("MISS")
