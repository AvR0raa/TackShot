import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
start = s.index("QImage Overlay::renderTranslated(")
end = s.index("void Overlay::onOcr()")
new = r'''QImage Overlay::renderTranslated(const QImage& base, const QVector<OcrLine>& lines,
                                 const QStringList& translated) {
    QImage out = base.convertToFormat(QImage::Format_ARGB32);
    QPainter p(&out);
    p.setRenderHint(QPainter::TextAntialiasing, true);
    for (int i = 0; i < lines.size() && i < translated.size(); ++i) {
        if (translated[i].trimmed().isEmpty()) continue;
        const QRect box = lines[i].box;
        // 擦除区域比文本框略大，盖住原字的上下缘
        QRect erase(box.left() - 4, box.top() - int(box.height() * 0.22),
                    box.width() + 8, int(box.height() * 1.44));
        erase = erase.intersected(out.rect());
        if (erase.width() < 6 || erase.height() < 6) continue;

        // 背景色：从文本框外侧一圈取样（避开笔画）
        long long sr = 0, sg = 0, sb = 0; int n = 0;
        auto sample = [&](int x, int y) {
            if (x < 0 || y < 0 || x >= out.width() || y >= out.height()) return;
            QRgb c = out.pixel(x, y);
            sr += qRed(c); sg += qGreen(c); sb += qBlue(c); n++;
        };
        for (int x = box.left(); x <= box.right(); x += 3) {
            sample(x, box.top() - 4);
            sample(x, box.bottom() + 4);
        }
        QColor bg = n ? QColor(int(sr / n), int(sg / n), int(sb / n)) : QColor(Qt::white);
        QColor fg = (bg.lightnessF() > 0.55) ? QColor(25, 25, 25) : QColor(240, 240, 240);

        p.fillRect(erase, bg);

        QFont f(QStringLiteral("Microsoft YaHei"));
        int px = qMax(9, int(box.height() * 0.82));
        f.setPixelSize(px);
        QFontMetrics fm(f);
        const QString& text = translated[i];
        while (px > 8 && fm.horizontalAdvance(text) > erase.width()) {
            px -= 1;
            f.setPixelSize(px);
            fm = QFontMetrics(f);
        }
        p.setFont(f);
        p.setPen(fg);
        p.drawText(erase, Qt::AlignLeft | Qt::AlignVCenter, text);
    }
    p.end();
    return out;
}

'''
s = s[:start] + new + s[end:]
io.open(p, "w", encoding="utf-8").write(s)
print("render improved")
