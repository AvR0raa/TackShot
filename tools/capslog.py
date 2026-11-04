import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()

# 抓屏前写诊断日志，便于远程定位 DPI 拉伸
old = """static void doCapture() {
    QString err;
    QRect rect;
    QImage shot = capture::captureVirtualDesktop(&rect, &err);"""
new = """static void captureLog(const QString& line) {
    QFile f(Config::get().dataDir() + "/capture.log");
    if (!f.open(QIODevice::Append)) return;
    f.write(QString("[%1] %2\\n")
                .arg(QDateTime::currentDateTime().toString("MM-dd HH:mm:ss"), line).toUtf8());
    f.close();
}

static void doCapture() {
    QString err;
    QRect rect;
    QImage shot = capture::captureVirtualDesktop(&rect, &err);"""
if old in s:
    s = s.replace(old, new, 1)

old2 = """    showOverlay(shot, rect, dpr);"""
new2 = """    {
        QString diag = QString("cursor=%1,%2 screens=")
                           .arg(QCursor::pos().x()).arg(QCursor::pos().y());
        for (QScreen* sc : screens)
            diag += QString("[%1 %2,%3 %4x%5 dpr=%6]")
                        .arg(sc->name()).arg(sc->geometry().x()).arg(sc->geometry().y())
                        .arg(sc->geometry().width()).arg(sc->geometry().height())
                        .arg(sc->devicePixelRatio());
        diag += QString(" mixed=%1 shot=%2x%3 physRect=%4,%5 %6x%7 dpr=%8")
                    .arg(mixed ? 1 : 0).arg(shot.width()).arg(shot.height())
                    .arg(rect.x()).arg(rect.y()).arg(rect.width()).arg(rect.height()).arg(dpr);
        captureLog(diag);
    }
    showOverlay(shot, rect, dpr);"""
if old2 in s:
    s = s.replace(old2, new2, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("capture diagnostic log added")
