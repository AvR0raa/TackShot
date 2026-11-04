#pragma once
#include <QString>
#include <QImage>
#include <QVector>
#include <QDateTime>

namespace hisimport {

struct Record {
    QString path;
    QDateTime time;
    qint64  size = 0;
    QImage  image;
};

QString historyDir();
QVector<Record> scan();

// 从 .his 中提取内嵌 PNG（元数据 + PNG + 尾部元数据的自研容器）
QImage extractPng(const QString& path);

} // namespace hisimport
