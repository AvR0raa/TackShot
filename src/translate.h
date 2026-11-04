#pragma once
#include <QString>
#include <QStringList>
#include <QObject>
#include <QHash>
#include <QVector>

struct ProviderPreset {
    QString id;
    QString name;
    QString baseUrl;      // 不含 /chat/completions
    QString model;
    QString note;
};

struct TranslateResult {
    bool ok = false;
    QString text;
    QString error;
    int httpStatus = 0;
    QString providerId;
    QString model;
    int attempts = 1;
    int chunkCount = 0;      // 分了几段
    int chunkFailed = 0;     // 失败几段
    bool fromCache = false;
};

// 译文缓存（jsonl，LRU 上限 5MB）
class TranslateCache {
public:
    static TranslateCache& get();
    QString lookup(const QString& key);
    void store(const QString& key, const QString& value);
    void clear();
    int size() const { return m_map.size(); }
private:
    void load();
    void save();
    QHash<QString, QString> m_map;
    QStringList m_order;
    bool m_loaded = false;
};

// OpenAI 兼容的翻译客户端
class TranslateClient : public QObject {
    Q_OBJECT
public:
    explicit TranslateClient(QObject* parent = nullptr);

    static QVector<ProviderPreset> presets();
    static ProviderPreset presetById(const QString& id);

    static QStringList splitChunks(const QString& text, int maxChars);

    // 整段翻译：自动分块、走缓存、注入术语表
    TranslateResult translateLong(const QString& text, const QString& targetLang,
                                  const ProviderPreset& p, const QString& apiKey,
                                  const QString& glossary = QString(),
                                  int chunkChars = 1500,
                                  bool useCache = true,
                                  const QString& sourceLang = QString());

    // 单行翻译（图片回填用，不走缓存）
    TranslateResult translateLine(const QString& text, const QString& targetLang,
                                  const ProviderPreset& p, const QString& apiKey,
                                  const QString& glossary = QString(),
                                  const QString& sourceLang = QString());

    TranslateResult testConnection(const ProviderPreset& p, const QString& apiKey);

private:
    TranslateResult doRequest(const QString& text, const QString& targetLang,
                              const ProviderPreset& p, const QString& apiKey,
                              int timeoutMs, bool allowRetry, const QString& glossary = QString(),
                              const QString& sourceLang = QString());
    QString buildPrompt(const QString& targetLang, const QString& glossary,
                        const QString& sourceLang = QString()) const;
};
