#include "longshot.h"
#include <QtMath>
#include <QPainter>
#include <QTransform>
#include <QVector>
#include <algorithm>
#include <cstdlib>

namespace {

// 缩放到固定宽度并转灰度
QVector<quint8> grayStrip(const QImage& img, int targetW, int* outH) {
    QImage s = img.scaledToWidth(targetW, Qt::SmoothTransformation)
                  .convertToFormat(QImage::Format_Grayscale8);
    int h = s.height();
    QVector<quint8> out(h * targetW);
    for (int y = 0; y < h; ++y) {
        const uchar* line = s.constScanLine(y);
        memcpy(out.data() + y * targetW, line, targetW);
    }
    *outH = h;
    return out;
}

} // namespace

namespace longshot {

QImage appendFrame(const QImage& canvas, const QImage& frame, bool* matched) {
    if (matched) *matched = false;
    if (frame.isNull()) return canvas;
    if (canvas.isNull()) return frame;
    if (canvas.width() != frame.width()) return canvas;

    const int TW = 240;                 // 匹配用宽度
    int ch = 0, fh = 0;
    QVector<quint8> cg = grayStrip(canvas, TW, &ch);
    QVector<quint8> fg = grayStrip(frame, TW, &fh);

    // 模板：画布底部一段
    int th = std::max(16, std::min(ch / 8, 40));
    if (th > ch) th = ch;
    if (fh <= th) return canvas;

    const int maxY = fh - th;
    int bestY = -1;
    double bestScore = 1e18;

    for (int y = 0; y <= maxY; ++y) {
        // 粗筛：每 4 行取一行
        double sad = 0;
        for (int r = 0; r < th; r += 4) {
            const quint8* a = cg.constData() + (ch - th + r) * TW;
            const quint8* b = fg.constData() + (y + r) * TW;
            for (int x = 0; x < TW; ++x)
                sad += std::abs(int(a[x]) - int(b[x]));
        }
        if (sad < bestScore) { bestScore = sad; bestY = y; }
    }
    if (bestY < 0) return canvas;

    int samples = (th + 3) / 4 * TW;
    double meanSad = bestScore / std::max(1, samples);
    if (meanSad > 8.0) return canvas;      // 不匹配（页面没滚动或完全变了）

    // 几何关系：模板首行在画布中的位置 (canvas.h - th/scale)，
    // 在帧中的位置 bestY/scale，由此得重叠行数 = (th + bestY) / scale
    double scale = double(ch) / std::max(1, canvas.height());
    int overlapOrig = int(std::lround((th + bestY) / std::max(1e-6, scale)));
    overlapOrig = std::max(0, std::min(overlapOrig, frame.height()));

    if (overlapOrig >= frame.height()) return canvas;   // 没有新内容

    QImage out(canvas.width(), canvas.height() + (frame.height() - overlapOrig), canvas.format());
    {
        QPainter p(&out);
        p.drawImage(0, 0, canvas);
        p.drawImage(0, canvas.height(), frame, 0, overlapOrig, frame.width(),
                    frame.height() - overlapOrig);
    }
    if (matched) *matched = true;
    return out;
}


QImage appendFrameH(const QImage& canvas, const QImage& frame, bool* matched) {
    if (frame.isNull()) return canvas;
    if (canvas.isNull()) return frame;
    QTransform tr(0, 1, 1, 0, 0, 0);   // 转置：x<->y
    QImage c = canvas.transformed(tr);
    QImage f = frame.transformed(tr);
    QImage r = appendFrame(c, f, matched);
    return r.transformed(tr);
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

} // namespace longshot
