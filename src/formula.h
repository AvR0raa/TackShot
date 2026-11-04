#pragma once
#include <QImage>
#include <QString>
#include <QStringList>
#include <QVector>

// 本地公式识别（pix2text-mfr-1.5，TrOCR 编码器-解码器，ONNX Runtime）
// 输出 LaTeX；模型目录默认 <exe>/models/formula
class FormulaRecognizer {
public:
    static FormulaRecognizer& get();

    bool init(const QString& modelDir = QString(), QString* err = nullptr);
    bool ready() const { return m_ready; }
    QString lastError() const { return m_error; }
    QString modelDir() const { return m_dir; }

    // 识别单张公式图；失败或未初始化返回空串
    QString recognize(const QImage& img);

    void release();

private:
    FormulaRecognizer() = default;
    ~FormulaRecognizer();
    bool loadVocab(const QString& path);

    bool m_ready = false;
    QString m_error;
    QString m_dir;
    QStringList m_idToToken;
    void* m_detEnv = nullptr;     // OrtEnv*
    void* m_enc = nullptr;        // OrtSession*
    void* m_dec = nullptr;
    void* m_memInfo = nullptr;
    int m_hiddenLen = 0;          // 编码器序列长度（578）
    int m_hiddenDim = 0;          // 384
};
