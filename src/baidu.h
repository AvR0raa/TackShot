#pragma once
#include <QImage>
#include <QObject>
#include <QRect>
#include <QString>
#include <QVector>

// 百度图片翻译（开放平台 /api/trans/sdk/picture）
// 一次调用即可拿到：分段原文 + 译文 + 文字坐标 + 整图贴合结果
struct BaiduLine {
    QString src;
    QString dst;
    QRect   rect;      // 原图坐标
};

struct BaiduResult {
    bool ok = false;
    QString error;
    int errorCode = 0;
    QString from;
    QString to;
    QVector<BaiduLine> lines;
    QString sumSrc;
    QString sumDst;
    QImage  pasteImage;   // paste=1/2 且成功时的贴合图
};

class BaiduPictureTranslate : public QObject {
public:
    explicit BaiduPictureTranslate(QObject* parent = nullptr);

    // appId/secret: 开放平台控制台的 APPID 与密钥
    // paste: 0 关闭贴合 / 1 整图贴合 / 2 分块贴合
    BaiduResult translate(const QImage& img, const QString& from, const QString& to,
                          const QString& appId, const QString& secret,
                          int paste = 1, int timeoutMs = 30000);
};
