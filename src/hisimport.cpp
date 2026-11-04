#include "hisimport.h"
#include <QDir>
#include <QDateTime>
#include <QFile>
#include <QFileInfo>
#include <QDebug>

namespace hisimport {

QString historyDir() {
    return qEnvironmentVariable("LOCALAPPDATA") + "/PixPin/History/_ScreenshotRecord";
}

QImage extractPng(const QString& path) {
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly)) return QImage();
    QByteArray data = f.readAll();
    f.close();
    int start = data.indexOf("\x89PNG\r\n\x1a\n");
    if (start < 0) return QImage();
    // 找 IEND 块：长度(4)+"IEND"(4)+CRC(4)，CRC 末尾固定 AE 42 60 82
    int iend = data.indexOf("IEND", start);
    int end = -1;
    while (iend > 0) {
        if (iend + 8 <= data.size() &&
            (unsigned char)data[iend + 4] == 0xAE && (unsigned char)data[iend + 5] == 0x42 &&
            (unsigned char)data[iend + 6] == 0x60 && (unsigned char)data[iend + 7] == 0x82) {
            end = iend + 8;
            break;
        }
        iend = data.indexOf("IEND", iend + 4);
    }
    if (end < 0) return QImage();
    QImage img;
    img.loadFromData(data.mid(start, end - start), "PNG");
    return img;
}

QVector<Record> scan() {
    QVector<Record> out;
    QDir d(historyDir());
    if (!d.exists()) return out;
    for (const QFileInfo& fi : d.entryInfoList({"*.his"}, QDir::Files, QDir::Time)) {
        Record r;
        r.path = fi.absoluteFilePath();
        r.size = fi.size();
        r.time = fi.lastModified();
        out.append(r);
    }
    return out;
}

} // namespace hisimport
