#include "gifenc.h"
#include <QPainter>
#include <QQueue>
#include <algorithm>
#include <cstring>

namespace {

struct Box { int r0, r1, g0, g1, b0, b1; int count; };

void put16(QFile& f, quint16 v) { f.putChar(char(v & 0xff)); f.putChar(char(v >> 8)); }

} // namespace

bool GifEncoder::open(const QString& path, int width, int height, int delayCs) {
    m_file.setFileName(path);
    if (!m_file.open(QIODevice::WriteOnly)) return false;
    m_w = width; m_h = height; m_delay = delayCs; m_frames = 0; m_closed = false;
    m_palette.clear();
    return true;
}

// 5-5-5 直方图 + 中位切分
void GifEncoder::buildPalette(const QVector<QImage>& frames) {
    const int B = 32;
    std::vector<int> hist(B * B * B, 0);
    for (const QImage& img : frames) {
        QImage s = img.scaled(160, 160, Qt::IgnoreAspectRatio, Qt::FastTransformation)
                      .convertToFormat(QImage::Format_RGB32);
        for (int y = 0; y < s.height(); ++y) {
            const QRgb* line = reinterpret_cast<const QRgb*>(s.constScanLine(y));
            for (int x = 0; x < s.width(); ++x) {
                QRgb c = line[x];
                int r = qRed(c) >> 3, g = qGreen(c) >> 3, b = qBlue(c) >> 3;
                hist[(r * B + g) * B + b]++;
            }
        }
    }
    struct Bin { int r, g, b, n; };
    std::vector<Bin> bins;
    for (int r = 0; r < B; ++r)
        for (int g = 0; g < B; ++g)
            for (int b = 0; b < B; ++b) {
                int n = hist[(r * B + g) * B + b];
                if (n) bins.push_back({r, g, b, n});
            }
    if (bins.empty()) { m_palette.append(qRgb(0, 0, 0)); return; }

    struct Node { std::vector<Bin> items; int count; };
    std::vector<Node> nodes;
    nodes.push_back({bins, 0});
    for (auto& n : nodes) for (auto& b : n.items) n.count += b.n;

    while (nodes.size() < 256) {
        // 找样本数最多且可再分的盒子
        int best = -1; long long bestCount = 0;
        for (int i = 0; i < int(nodes.size()); ++i) {
            if (nodes[i].items.size() < 2) continue;
            if (nodes[i].count > bestCount) { bestCount = nodes[i].count; best = i; }
        }
        if (best < 0) break;
        auto items = nodes[best].items;
        // 选择跨度最大的通道
        int mr = 0, mg = 0, mb = 0;
        int r0 = 99, r1 = -1, g0 = 99, g1 = -1, b0 = 99, b1 = -1;
        for (auto& b : items) {
            r0 = std::min(r0, b.r); r1 = std::max(r1, b.r);
            g0 = std::min(g0, b.g); g1 = std::max(g1, b.g);
            b0 = std::min(b0, b.b); b1 = std::max(b1, b.b);
        }
        mr = r1 - r0; mg = g1 - g0; mb = b1 - b0;
        int chan = (mr >= mg && mr >= mb) ? 0 : (mg >= mb ? 1 : 2);
        std::sort(items.begin(), items.end(), [chan](const Bin& a, const Bin& b) {
            return chan == 0 ? a.r < b.r : (chan == 1 ? a.g < b.g : a.b < b.b);
        });
        long long half = nodes[best].count / 2, acc = 0;
        size_t split = 1;
        for (size_t i = 0; i < items.size(); ++i) {
            acc += items[i].n;
            if (acc >= half) { split = std::max<size_t>(1, std::min(items.size() - 1, i + 1)); break; }
        }
        Node a, c;
        a.items.assign(items.begin(), items.begin() + split);
        c.items.assign(items.begin() + split, items.end());
        a.count = 0; c.count = 0;
        for (auto& b : a.items) a.count += b.n;
        for (auto& b : c.items) c.count += b.n;
        nodes[best] = a;
        nodes.push_back(c);
    }

    m_palette.clear();
    for (auto& n : nodes) {
        long long r = 0, g = 0, b = 0, cnt = 0;
        for (auto& x : n.items) { r += x.r * x.n; g += x.g * x.n; b += x.b * x.n; cnt += x.n; }
        if (!cnt) continue;
        m_palette.append(qRgb(int(r / cnt) << 3, int(g / cnt) << 3, int(b / cnt) << 3));
    }
    while (m_palette.size() < 256) m_palette.append(m_palette.last());
}

quint8 GifEncoder::mapColor(QRgb c) const {
    // 5-5-5 索引表加速
    int r = qRed(c) >> 3, g = qGreen(c) >> 3, b = qBlue(c) >> 3;
    int best = 0; int bestD = 1 << 30;
    for (int i = 0; i < m_palette.size() && i < 256; ++i) {
        QRgb p = m_palette[i];
        int dr = r - (qRed(p) >> 3), dg = g - (qGreen(p) >> 3), db = b - (qBlue(p) >> 3);
        int d = dr * dr + dg * dg + db * db;
        if (d < bestD) { bestD = d; best = i; if (!d) break; }
    }
    return quint8(best);
}

void GifEncoder::writeLzw(const QVector<quint8>& idx) {
    const int minCodeSize = 8;
    m_file.putChar(char(minCodeSize));
    QHash<quint32, int> table;
    int nextCode = (1 << minCodeSize) + 2;
    int codeSize = minCodeSize + 1;
    QVector<quint8> block;
    auto flushBlock = [&]() {
        if (block.isEmpty()) return;
        m_file.putChar(char(block.size()));
        m_file.write(reinterpret_cast<const char*>(block.constData()), block.size());
        block.clear();
    };
    int bitBuf = 0, bitCnt = 0;
    auto emitCode = [&](int code) {
        bitBuf |= (code << bitCnt);
        bitCnt += codeSize;
        while (bitCnt >= 8) {
            block.append(quint8(bitBuf & 0xff));
            bitBuf >>= 8; bitCnt -= 8;
            if (block.size() >= 255) flushBlock();
        }
    };

    emitCode(1 << minCodeSize);   // clear code
    int prev = idx.isEmpty() ? -1 : idx[0];
    for (int i = 1; i < idx.size(); ++i) {
        int c = idx[i];
        quint32 key = (quint32(prev) << 8) | quint32(c);
        auto it = table.constFind(key);
        if (it != table.constEnd()) {
            prev = it.value();
            continue;
        }
        emitCode(prev);
        table.insert(key, nextCode++);
        if (nextCode > (1 << codeSize) && codeSize < 12) ++codeSize;
        if (nextCode >= 4096) {
            emitCode(1 << minCodeSize);
            table.clear();
            nextCode = (1 << minCodeSize) + 2;
            codeSize = minCodeSize + 1;
        }
        prev = c;
    }
    if (prev >= 0) emitCode(prev);
    emitCode(nextCode);           // EOI
    if (bitCnt > 0) {
        block.append(quint8(bitBuf & 0xff));
        if (block.size() >= 255) flushBlock();
    }
    flushBlock();
    m_file.putChar(0);        // block terminator
}

bool GifEncoder::addFrame(const QImage& src) {
    if (m_closed || m_w <= 0) return false;
    if (m_frames == 0) buildPalette({src});

    QImage img = src.scaled(m_w, m_h, Qt::IgnoreAspectRatio, Qt::SmoothTransformation)
                    .convertToFormat(QImage::Format_RGB32);

    if (m_frames == 0) {
        // 头 + 逻辑屏幕描述符 + 全局调色板
        m_file.write("GIF89a", 6);
        put16(m_file, quint16(m_w));
        put16(m_file, quint16(m_h));
        m_file.putChar(char(0xF7));   // 全局调色板 256 色
        m_file.putChar(char(0));      // 背景色
        m_file.putChar(char(0));      // 像素宽高比
        for (int i = 0; i < 256; ++i) {
            QRgb c = i < m_palette.size() ? m_palette[i] : qRgb(0, 0, 0);
            m_file.putChar(char(qRed(c)));
            m_file.putChar(char(qGreen(c)));
            m_file.putChar(char(qBlue(c)));
        }
        // Netscape 循环扩展
        m_file.putChar(char(0x21)); m_file.putChar(char(0xFF)); m_file.putChar(char(11));
        m_file.write("NETSCAPE2.0", 11);
        m_file.putChar(char(3)); m_file.putChar(char(1));
        put16(m_file, 0);
        m_file.putChar(char(0));
    }

    QVector<quint8> idx(m_w * m_h);
    for (int y = 0; y < m_h; ++y) {
        const QRgb* line = reinterpret_cast<const QRgb*>(img.constScanLine(y));
        for (int x = 0; x < m_w; ++x)
            idx[y * m_w + x] = mapColor(line[x]);
    }

    // 图形控制扩展
    m_file.putChar(char(0x21)); m_file.putChar(char(0xF9)); m_file.putChar(char(4));
    m_file.putChar(char(0x04));                     // disposal=1, 无透明
    put16(m_file, quint16(m_delay));
    m_file.putChar(char(0));
    m_file.putChar(char(0));

    // 图像描述符
    m_file.putChar(char(0x2C));
    put16(m_file, 0); put16(m_file, 0);
    put16(m_file, quint16(m_w)); put16(m_file, quint16(m_h));
    m_file.putChar(char(0));                        // 无局部调色板

    writeLzw(idx);
    m_frames++;
    return true;
}

bool GifEncoder::close() {
    if (m_closed) return true;
    m_closed = true;
    m_file.putChar(char(0x3B));
    m_file.close();
    return m_frames > 0;
}
