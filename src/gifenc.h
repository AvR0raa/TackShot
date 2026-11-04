#pragma once
#include <QImage>
#include <QString>
#include <QFile>
#include <QVector>
#include <QHash>

// 极简 GIF89a 编码器：全局调色板（中位切分）+ LZW
class GifEncoder {
public:
    bool open(const QString& path, int width, int height, int delayCs = 10);
    bool addFrame(const QImage& frame);     // 自动转换为 RGB888
    bool close();
    int  frameCount() const { return m_frames; }

private:
    void buildPalette(const QVector<QImage>& frames);
    quint8 mapColor(QRgb c) const;
    void writeLzw(const QVector<quint8>& idx);

    QFile m_file;
    int m_w = 0, m_h = 0, m_delay = 10, m_frames = 0;
    QVector<QRgb> m_palette;   // 最多 256
    bool m_closed = false;
};
