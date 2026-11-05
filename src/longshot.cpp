#include "longshot.h"
#include <QtMath>
#include <QPainter>
#include <QTransform>
#include <QVector>
#include <algorithm>
#include <cstdlib>
#include <cstdarg>
#include <cstdio>
#include <QDebug>

namespace {
// 诊断开关：设 TACKSHOT_LS_DEBUG=1 时输出匹配决策细节
bool lsDebug() {
    static const bool on = qEnvironmentVariableIsSet("TACKSHOT_LS_DEBUG");
    return on;
}
void lsLog(const char* fmt, ...) {
    va_list ap; va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fflush(stderr);
}

// 两图同 y 行是否逐像素一致（抽样灰差均值 < 3）
bool rowSame(const QImage& a, const QImage& b, int y) {
    if (a.width() != b.width() || a.depth() != 32 || b.depth() != 32) return false;
    const QRgb* ra = reinterpret_cast<const QRgb*>(a.constScanLine(y));
    const QRgb* rb = reinterpret_cast<const QRgb*>(b.constScanLine(y));
    long long d = 0; int n = 0;
    for (int x = 0; x < a.width(); x += 5) {
        d += std::abs(qGray(ra[x]) - qGray(rb[x]));
        ++n;
    }
    return n && d / n < 3;
}
}

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

QImage appendFrame(const QImage& canvasIn, const QImage& frameIn, bool* matched) {
    if (matched) *matched = false;
    if (frameIn.isNull()) return canvasIn;
    if (canvasIn.isNull()) return frameIn;
    if (canvasIn.width() != frameIn.width()) return canvasIn;

    QImage canvas = canvasIn, frame = frameIn;
    // 固定元素（sticky 顶栏/底栏）感知：两图顶部逐行相同的静态前缀不属于滚动几何。
    // 从帧中剔除前缀后按纯平移拼接——固定栏画布首帧已包含，不重复、不错位。
    // （画布拼接后比帧高，只要求同宽即可；画布顶部始终是首帧原样）
    if (canvas.width() == frame.width() && canvas.depth() == 32 && frame.depth() == 32) {
        const int SMAX = qMin(canvas.height(), frame.height()) * 2 / 3;
        int S = 0;
        while (S < SMAX && rowSame(canvas, frame, S)) ++S;
        if (S >= 40) {
            frame = frame.copy(0, S, frame.width(), frame.height() - S);
            if (lsDebug()) lsLog("[ls] sticky header %d rows stripped\n", S);
        }
    }
    if (frame.height() < 48) return canvasIn;

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
    double bestScore = 1e18, secondScore = 1e18;

    for (int y = 0; y <= maxY; ++y) {
        // 粗筛：每 4 行取一行
        double sad = 0;
        for (int r = 0; r < th; r += 4) {
            const quint8* a = cg.constData() + (ch - th + r) * TW;
            const quint8* b = fg.constData() + (y + r) * TW;
            for (int x = 0; x < TW; ++x)
                sad += std::abs(int(a[x]) - int(b[x]));
        }
        if (sad < bestScore) {
            secondScore = bestScore;      // 旧最优降级为次优
            bestScore = sad; bestY = y;
        } else if (sad < secondScore && std::abs(y - bestY) > th) {
            secondScore = sad;            // 与最优不相邻的候选才可作次优（相邻位置天然相似）
        }
    }
    if (bestY < 0) return canvas;

    int samples = (th + 3) / 4 * TW;
    double meanSad = bestScore / std::max(1, samples);
    if (lsDebug())
        lsLog("[ls] bestY=%d meanSad=%.2f second=%.2f\n", bestY, meanSad,
              secondScore / samples);
    if (meanSad > 5.0) return canvas;      // 不匹配（页面没滚动或完全变了）
    // 歧义检查：别处存在几乎同样好的候选（重复纹理）且最优并非完全一致时，
    // 拼接位置不可信——宁可不拼也不能接错（错位重影比丢帧更难看）。
    if (meanSad > 0.5 && secondScore < bestScore * 1.15) {
        if (lsDebug()) lsLog("[ls] rejected: ambiguous\n");
        return canvas;
    }

    // 几何关系：模板首行在画布中的位置 (canvas.h - th/scale)，
    // 在帧中的位置 bestY/scale，由此得重叠行数 = (th + bestY) / scale
    double scale = double(ch) / std::max(1, canvas.height());
    int overlapOrig = int(std::lround((th + bestY) / std::max(1e-6, scale)));
    overlapOrig = std::max(0, std::min(overlapOrig, frame.height()));

    if (overlapOrig >= frame.height()) return canvas;   // 没有新内容

    // 原分辨率微调 + 复核：缩放坐标换算存在 1/scale（约 3px）量化误差，
    // 在 ±8 行内找最优整体行偏移修正 overlap（顺带把拼接对齐提到像素级），
    // 再用修正后的结果复核——错配（任何偏移下内容都对不上）在此被拒。
    if (canvas.format() == frame.format() && canvas.depth() == 32) {
        double bestDiff = 1e18; int bestOff = 0;
        for (int off = -8; off <= 8; ++off) {
            const int ov = overlapOrig + off;
            if (ov <= 0 || ov > frame.height()) continue;
            double d = 0; int n = 0;
            const int stepY = std::max(1, ov / 40);
            for (int y = 0; y < ov; y += stepY) {
                const QRgb* a = reinterpret_cast<const QRgb*>(
                    canvas.constScanLine(canvas.height() - ov + y));
                const QRgb* b = reinterpret_cast<const QRgb*>(frame.constScanLine(y));
                for (int x = 0; x < canvas.width(); x += 7) {
                    d += std::abs(qGray(a[x]) - qGray(b[x]));
                    ++n;
                }
            }
            if (n && d / n < bestDiff) { bestDiff = d / n; bestOff = off; }
        }
        overlapOrig = std::max(1, std::min(overlapOrig + bestOff, frame.height()));
        if (bestDiff > 6.0) {
            if (lsDebug()) lsLog("[ls] rejected: verify diff=%.2f off=%d overlap=%d\n",
                                 bestDiff, bestOff, overlapOrig);
            return canvas;
        }
        if (lsDebug()) lsLog("[ls] refined off=%d diff=%.2f overlap=%d\n",
                             bestOff, bestDiff, overlapOrig);
    }

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


int verticalShift(const QImage& prev, const QImage& cur) {
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
