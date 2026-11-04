#pragma once
#include <QImage>
#include <QObject>
#include <QString>

struct SimpleTexResult {
    bool ok = false;
    QString latex;
    QString error;
    double confidence = 0.0;
    int httpStatus = 0;
};

// SimpleTex 公式识别（POST multipart，header token: <UAT>）
class SimpleTexClient : public QObject {
public:
    explicit SimpleTexClient(QObject* parent = nullptr);

    // light=true 用轻量模型（latex_ocr_turbo，更便宜更快）
    SimpleTexResult recognize(const QImage& img, const QString& token,
                              bool light = true, int timeoutMs = 30000);
};
