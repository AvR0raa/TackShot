#pragma once
#include <QImage>
#include <QString>
#include <QStringList>
#include <QRect>
#include <QVector>

struct OcrLine {
    QString text;
    float   score = 0.0f;
    QRect   box;
};

// 本地 OCR（PP-OCRv4 det + rec，ONNX Runtime）
class Ocr {
public:
    static Ocr& get();

    // 从 exe 同目录的 models/ 加载；返回 false 表示不可用
    bool init(QString* err = nullptr);
    bool ready() const { return m_ready; }
    QString lastError() const { return m_error; }

    QVector<OcrLine> recognize(const QImage& img, QString* err = nullptr);

private:
    Ocr() = default;
    bool loadSessions();
    void release();

    bool m_ready = false;
    QString m_error;
    QStringList m_dict;
    void* m_api = nullptr;        // const OrtApi*
    void* m_env = nullptr;
    void* m_det = nullptr;
    void* m_rec = nullptr;
    void* m_memInfo = nullptr;
};
