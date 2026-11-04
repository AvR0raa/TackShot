#pragma once
#include <QString>
#include <QObject>
#include <QImage>

// 在线视觉识别结果
struct VisionResult {
    bool ok = false;
    QString text;
    QString error;
    int httpStatus = 0;
    QString model;
};

// OpenAI 兼容的视觉识别客户端（同步调用，与 TranslateClient 一致）
// 注意：本类不保存任何 Key，仅使用调用方传入的临时值。
class VisionClient : public QObject {
public:
    explicit VisionClient(QObject* parent = nullptr);

    // 识别单张图片；prompt 为空时使用内置中文提示词
    VisionResult recognize(const QImage& img, const QString& prompt, const QString& baseUrl,
                           const QString& model, const QString& apiKey, int timeoutMs = 60000);

    // 探活：发一张极小的测试图，检查地址 / Key / 模型是否可用
    VisionResult probe(const QString& baseUrl, const QString& model, const QString& apiKey);

private:
    VisionResult doRequest(const QImage& img, const QString& prompt, const QString& baseUrl,
                           const QString& model, const QString& apiKey, int timeoutMs,
                           bool allowRetry, bool allowEmpty);
};
