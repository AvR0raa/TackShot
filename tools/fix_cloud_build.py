import io

# main.cpp：用合成行替代本地 OCR
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
old = """        Ocr& ocr = Ocr::get();
        QString err;
        bool ocrOk = ocr.init(&err);
        QVector<OcrLine> lines = ocrOk ? ocr.recognize(img, &err) : QVector<OcrLine>();"""
new = """        QString err;
        // 本地模型已移除：这里用合成行验证“译文回填”渲染链路
        QVector<OcrLine> lines;
        {
            OcrLine a; a.text = QStringLiteral("Open file and save as"); a.score = 0.99f;
            a.box = QRect(47, 44, 420, 36); lines.append(a);
            OcrLine b; b.text = QStringLiteral("Settings panel"); b.score = 0.98f;
            b.box = QRect(46, 112, 300, 36); lines.append(b);
            OcrLine c; c.text = QStringLiteral("Exit application"); c.score = 0.97f;
            c.box = QRect(46, 183, 300, 36); lines.append(c);
        }
        bool ocrOk = !lines.isEmpty();"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("main: synthetic lines")

# overlay.cpp：恢复 physRegionOf
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
if "static QRect physRegionOf" not in s:
    s = s.replace("void Overlay::onLongShot() {",
"""// 选区（图像坐标）-> 物理屏幕矩形
static QRect physRegionOf(const QRect& physBase, const QRect& sel) {
    return QRect(physBase.topLeft() + sel.topLeft(), sel.size());
}

void Overlay::onLongShot() {""", 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("overlay: physRegionOf restored")
