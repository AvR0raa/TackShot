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

// 百度通用文本翻译（开放平台 /api/trans/vip/translate，与图片翻译共用 APPID/密钥）
struct BaiduTextResult {
    bool ok = false;
    QString text;       // 译文（多行按 \n 连接）
    QString error;
    int errorCode = 0;
    QString from;
    QString to;
};

class BaiduTextTranslate : public QObject {
public:
    explicit BaiduTextTranslate(QObject* parent = nullptr);

    // 一次调用可含多行（\n 分隔），标准版限 1 次/秒，54003 会自动等待重试
    static BaiduTextResult translate(const QString& text, const QString& from, const QString& to,
                                     const QString& appId, const QString& secret,
                                     int timeoutMs = 15000);
};

// 中文语言名 -> 百度语言码（图片 / 文本翻译通用）
QString baiduLangCode(const QString& name);

// 上传编码：小图(≤300KB)用 PNG 无损；大图自动转 JPG（q85→70→55 递降，再超限按 0.75 缩放重试），
// 控制在 maxBytes 内。大截图体积可降 5~10 倍，OCR 清晰度不受影响。失败返回空。
QByteArray encodeImageForUpload(const QImage& img, int maxBytes);
