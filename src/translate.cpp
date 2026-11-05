#include "translate.h"
#include "config.h"
#include "baidu.h"
#include "managed.h"
#include "secrets.h"

#include <QNetworkAccessManager>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QEventLoop>
#include <QTimer>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QUrl>
#include <QThread>
#include <QFile>
#include <QDir>
#include <QTextStream>
#include <QCryptographicHash>
#include <QRegularExpression>
#include <QDebug>

// ---------------- cache ----------------

TranslateCache& TranslateCache::get() {
    static TranslateCache c;
    return c;
}

static QString cachePath() { return Config::get().dataDir() + "/translate_cache.jsonl"; }

void TranslateCache::load() {
    if (m_loaded) return;
    m_loaded = true;
    QFile f(cachePath());
    if (!f.open(QIODevice::ReadOnly)) return;
    while (!f.atEnd()) {
        QByteArray line = f.readLine().trimmed();
        if (line.isEmpty()) continue;
        auto doc = QJsonDocument::fromJson(line);
        if (!doc.isObject()) continue;
        auto o = doc.object();
        const QString k = o["k"].toString(), v = o["v"].toString();
        if (k.isEmpty()) continue;
        if (!m_map.contains(k)) m_order.append(k);
        m_map[k] = v;
    }
    f.close();
    // 超限则丢最早的一半
    while (m_map.size() > 4000 && m_order.size() > 1) {
        const QString k = m_order.takeFirst();
        m_map.remove(k);
    }
}

void TranslateCache::save() {
    QDir().mkpath(Config::get().dataDir());
    QFile f(cachePath());
    if (!f.open(QIODevice::WriteOnly | QIODevice::Truncate)) return;
    QTextStream ts(&f);
    ts.setEncoding(QStringConverter::Utf8);
    for (const QString& k : m_order) {
        QJsonObject o; o["k"] = k; o["v"] = m_map.value(k);
        ts << QString::fromUtf8(QJsonDocument(o).toJson(QJsonDocument::Compact)) << "\n";
    }
    f.close();
}

QString TranslateCache::lookup(const QString& key) {
    load();
    if (!m_map.contains(key)) return QString();
    return m_map.value(key);
}

void TranslateCache::store(const QString& key, const QString& value) {
    load();
    if (!m_map.contains(key)) m_order.append(key);
    m_map[key] = value;
    while (m_map.size() > 4000 && m_order.size() > 1) {
        const QString k = m_order.takeFirst();
        m_map.remove(k);
    }
    save();
}

void TranslateCache::clear() {
    m_map.clear(); m_order.clear(); m_loaded = true;
    QFile::remove(cachePath());
}

// ---------------- client ----------------

TranslateClient::TranslateClient(QObject* parent) : QObject(parent) {}

QVector<ProviderPreset> TranslateClient::presets() {
    return {
        {"baidu", QStringLiteral("百度翻译（与识别共用 APPID）"),
         QString(), QStringLiteral("baidu-text"),
         QStringLiteral("复用「识别」页的百度 APPID/密钥；标准版限 1 次/秒")},
        {"deepseek", QStringLiteral("DeepSeek（中英推荐）"),
         QStringLiteral("https://api.deepseek.com"), QStringLiteral("deepseek-flash"),
         QStringLiteral("中英互译质量最好，按 token 计费")},
        {"gemini", QStringLiteral("Gemini（有免费额度）"),
         QStringLiteral("https://generativelanguage.googleapis.com/v1beta/openai"),
         QStringLiteral("gemini-3.8-flash"),
         QStringLiteral("欧语/长文强，免费层限速，注意隐私")},
        {"custom", QStringLiteral("自定义（OpenAI 兼容）"),
         QStringLiteral("http://127.0.0.1:11434/v1"), QStringLiteral("qwen2.5:7b"),
         QStringLiteral("自建 vLLM / Ollama / 中转站都填这里")},
    };
}

ProviderPreset TranslateClient::presetById(const QString& id) {
    for (const auto& p : presets())
        if (p.id == id) return p;
    return presets().first();
}

QString TranslateClient::buildPrompt(const QString& targetLang, const QString& glossary,
                                     const QString& sourceLang) const {
    const bool autoDetect = sourceLang.trimmed().isEmpty() ||
                            sourceLang.contains(QStringLiteral("自动"));
    QString head;
    if (autoDetect)
        head = QStringLiteral("你是专业翻译引擎。判断用户文本的语言，并翻译成%1。\n").arg(targetLang);
    else
        head = QStringLiteral("你是专业翻译引擎。把用户提供的%1文本翻译成%2。\n")
                   .arg(sourceLang, targetLang);
    QString s = head + QStringLiteral(
        "规则：\n"
        "1) 只输出译文，不要解释、不要加引号、不要输出原文；\n"
        "2) 保留段落、换行、列表编号与缩进；\n"
        "3) 代码、URL、邮箱、数字、专有名词原样保留；\n"
        "4) 如果原文已经是目标语言，原样返回。");
    if (!glossary.trimmed().isEmpty()) {
        s += QStringLiteral("\n5) 必须遵守以下术语表（左为原文，右为指定译法）：\n") + glossary.trimmed();
    }
    return s;
}

// 按段落/句子切块
QStringList TranslateClient::splitChunks(const QString& text, int maxChars) {
    QStringList out;
    if (text.isEmpty()) return out;
    if (maxChars < 100) maxChars = 100;

    const QStringList paragraphs = text.split('\n');
    QString cur;
    for (const QString& para : paragraphs) {
        if (para.size() > maxChars) {
            // 单段过长：先吐掉已有，再按句切
            if (!cur.isEmpty()) { out << cur; cur.clear(); }
            static const QRegularExpression sent(QStringLiteral("(?<=[。！？!?\\.;；])"));
            const QStringList parts = para.split(sent, Qt::KeepEmptyParts);
            QString piece;
            for (const QString& s : parts) {
                if (!piece.isEmpty() && piece.size() + s.size() > maxChars) {
                    out << piece; piece.clear();
                }
                if (s.size() > maxChars) {
                    for (int i = 0; i < s.size(); i += maxChars)
                        out << s.mid(i, maxChars);
                } else {
                    piece += s;
                }
            }
            if (!piece.isEmpty()) out << piece;
            continue;
        }
        if (!cur.isEmpty() && cur.size() + 1 + para.size() > maxChars) {
            out << cur; cur.clear();
        }
        if (!cur.isEmpty()) cur += "\n";
        cur += para;
    }
    if (!cur.isEmpty()) out << cur;
    return out;
}

TranslateResult TranslateClient::translateLong(const QString& text, const QString& targetLang,
                                               const ProviderPreset& p, const QString& apiKey,
                                               const QString& glossary, int chunkChars,
                                               bool useCache, const QString& sourceLang) {
    TranslateResult res;
    res.providerId = p.id;
    res.model = p.model;

    const QStringList chunks = splitChunks(text, chunkChars);
    res.chunkCount = chunks.size();
    if (chunks.isEmpty()) { res.error = QStringLiteral("没有可翻译的内容"); return res; }

    QStringList out;
    QString firstError;
    for (const QString& c : chunks) {
        QString key;
        if (useCache) {
            QCryptographicHash h(QCryptographicHash::Sha256);
            h.addData(c.toUtf8());
            h.addData("|" + p.model.toUtf8() + "|" + targetLang.toUtf8() + "|" + glossary.toUtf8()
                      + "|" + sourceLang.toUtf8());
            key = QString::fromLatin1(h.result().toHex());
            QString hit = TranslateCache::get().lookup(key);
            if (!hit.isEmpty()) { out << hit; res.fromCache = true; continue; }
        }
        TranslateResult r = doRequest(c, targetLang, p, apiKey, 45000, true, glossary, sourceLang);
        if (r.ok) {
            out << r.text;
            if (useCache) TranslateCache::get().store(key, r.text);
        } else {
            res.chunkFailed++;
            if (firstError.isEmpty()) firstError = r.error;
            out << QStringLiteral("【本段翻译失败：%1】").arg(r.error);
        }
    }
    res.text = out.join("\n");
    res.ok = (res.chunkFailed < chunks.size());
    res.error = res.ok ? QString() : firstError;
    return res;
}

TranslateResult TranslateClient::translateLine(const QString& text, const QString& targetLang,
                                               const ProviderPreset& p, const QString& apiKey,
                                               const QString& glossary, const QString& sourceLang) {
    return doRequest(text, targetLang, p, apiKey, 30000, false, glossary, sourceLang);
}

TranslateClient::BatchResult TranslateClient::translateBatch(
        const QStringList& lines, const QString& targetLang, const ProviderPreset& p,
        const QString& apiKey, const QString& glossary, const QString& sourceLang,
        const std::function<void(int, int)>& progress) {
    BatchResult res;
    res.lines = QStringList(lines.size(), QString());
    if (lines.isEmpty()) return res;

    // 百度：多行合并成一次请求（\n 分隔，trans_result 按行返回）；超 5000 字节分批
    if (p.id == QStringLiteral("baidu")) {
        Config& c = Config::get();
        const QString appId = c.baiduAppId.trimmed();
        const QString secret = !apiKey.trimmed().isEmpty() ? apiKey.trimmed()
                                                           : secrets::load("baidu_secret");
        if ((appId.isEmpty() || secret.isEmpty()) && !managed::available()) {
            res.failed = lines.size();
            res.error = QStringLiteral("百度翻译未配置 APPID/密钥（设置 → 识别），且无内置云代理");
            return res;
        }
        const QString from = baiduLangCode(sourceLang);
        const QString to = baiduLangCode(targetLang);

        struct Batch { QVector<int> idx; QStringList rows; int bytes = 0; };
        QVector<Batch> batches;
        int total = 0;
        for (int i = 0; i < lines.size(); ++i) {
            const QString t = lines[i].trimmed();
            if (t.isEmpty()) continue;   // 空行不发送（百度会丢弃导致错位）
            const int bytes = t.toUtf8().size() + 1;
            if (batches.isEmpty() || batches.last().bytes + bytes > 5000)
                batches.append(Batch());
            batches.last().idx.append(i);
            batches.last().rows << t;
            batches.last().bytes += bytes;
            ++total;
        }
        if (total == 0) { res.error = QStringLiteral("没有可翻译的内容"); return res; }

        int done = 0;
        for (int bi = 0; bi < batches.size(); ++bi) {
            if (bi > 0) QThread::msleep(1100);   // 标准版 QPS=1
            const BaiduTextResult r = BaiduTextTranslate::translate(
                batches[bi].rows.join(QLatin1Char('\n')), from, to, appId, secret);
            if (r.ok) {
                const QStringList dst = r.text.split(QLatin1Char('\n'));
                for (int k = 0; k < batches[bi].idx.size(); ++k) {
                    const QString v = (k < dst.size()) ? dst[k] : QString();
                    res.lines[batches[bi].idx[k]] = v;
                    if (v.isEmpty()) ++res.failed; else ++done;
                }
            } else {
                res.failed += batches[bi].idx.size();
                if (res.error.isEmpty()) res.error = r.error;
            }
            if (progress) progress(done, total);
        }
        return res;
    }

    // OpenAI 兼容引擎：内部逐行
    for (int i = 0; i < lines.size(); ++i) {
        const TranslateResult r = translateLine(lines[i], targetLang, p, apiKey,
                                                glossary, sourceLang);
        res.lines[i] = r.ok ? r.text : QString();
        if (!r.ok) {
            ++res.failed;
            if (res.error.isEmpty()) res.error = r.error;
        }
        if (progress) progress(i + 1, lines.size());
    }
    return res;
}

TranslateResult TranslateClient::testConnection(const ProviderPreset& p, const QString& apiKey) {
    return doRequest(QStringLiteral("Hello, world"), QStringLiteral("简体中文"),
                     p, apiKey, 20000, false, QString());
}

TranslateResult TranslateClient::doRequest(const QString& text, const QString& targetLang,
                                           const ProviderPreset& p, const QString& apiKey,
                                           int timeoutMs, bool allowRetry, const QString& glossary,
                                           const QString& sourceLang) {
    TranslateResult res;
    res.providerId = p.id;
    res.model = p.model;

    // 百度通用文本翻译：不走 OpenAI 协议，apiKey 传入的是百度密钥（留空则取 DPAPI 存储）；
    // 无用户凭据但有内置云代理时，BaiduTextTranslate 内部自动走托管模式
    if (p.id == QStringLiteral("baidu")) {
        Config& c = Config::get();
        const QString appId = c.baiduAppId.trimmed();
        const QString secret = !apiKey.trimmed().isEmpty() ? apiKey.trimmed()
                                                           : secrets::load("baidu_secret");
        if ((appId.isEmpty() || secret.isEmpty()) && !managed::available()) {
            res.error = QStringLiteral("百度翻译未配置 APPID/密钥（设置 → 识别），且无内置云代理");
            return res;
        }
        const BaiduTextResult r = BaiduTextTranslate::translate(
            text, baiduLangCode(sourceLang), baiduLangCode(targetLang), appId, secret);
        res.ok = r.ok;
        res.text = r.text;
        res.error = r.error;
        res.attempts = 1;
        return res;
    }

    QString endpoint = p.baseUrl;
    while (endpoint.endsWith('/')) endpoint.chop(1);
    if (!endpoint.endsWith("/chat/completions")) endpoint += "/chat/completions";

    QJsonObject sys;
    sys["role"] = "system";
    sys["content"] = buildPrompt(targetLang, glossary, sourceLang);
    QJsonObject user;
    user["role"] = "user";
    user["content"] = text;
    QJsonArray msgs; msgs.append(sys); msgs.append(user);

    QJsonObject body;
    body["model"] = p.model;
    body["messages"] = msgs;
    body["temperature"] = 0.2;
    body["stream"] = false;

    const int maxAttempts = allowRetry ? 3 : 1;
    for (int attempt = 1; attempt <= maxAttempts; ++attempt) {
        res.attempts = attempt;
        QNetworkAccessManager mgr;
        QNetworkRequest req{QUrl(endpoint)};
        req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
        req.setRawHeader("Authorization", ("Bearer " + apiKey).toUtf8());
        req.setRawHeader("User-Agent", "TackShot/1.6");
        req.setTransferTimeout(timeoutMs);

        QNetworkReply* reply = mgr.post(req, QJsonDocument(body).toJson(QJsonDocument::Compact));
        QEventLoop loop;
        QTimer timer;
        timer.setSingleShot(true);
        bool timedOut = false;
        QObject::connect(&timer, &QTimer::timeout, [&]() { timedOut = true; reply->abort(); });
        QObject::connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);
        timer.start(timeoutMs);
        loop.exec();
        timer.stop();

        const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QByteArray payload = reply->readAll();
        const QString nerrStr = reply->errorString();
        reply->deleteLater();
        res.httpStatus = status;

        if (timedOut) {
            res.error = QStringLiteral("请求超时（%1s）").arg(timeoutMs / 1000);
        } else if (status == 0) {
            res.error = QStringLiteral("网络错误：%1").arg(nerrStr);
        } else if (status == 401 || status == 403) {
            res.error = QStringLiteral("API Key 无效或无权限（HTTP %1）").arg(status);
            return res;
        } else if (status == 402) {
            res.error = QStringLiteral("账户余额不足（HTTP 402）");
            return res;
        } else if (status == 429) {
            res.error = QStringLiteral("触发限流（HTTP 429）");
        } else if (status >= 500) {
            res.error = QStringLiteral("服务端错误（HTTP %1）").arg(status);
        } else if (status == 200) {
            auto doc = QJsonDocument::fromJson(payload);
            QString content;
            if (doc.isObject()) {
                auto o = doc.object();
                if (o.contains("choices")) {
                    auto arr = o["choices"].toArray();
                    if (!arr.isEmpty()) {
                        auto m = arr[0].toObject()["message"].toObject();
                        content = m["content"].toString();
                        if (content.isEmpty()) content = m["reasoning_content"].toString();
                    }
                } else if (o.contains("error")) {
                    res.error = QStringLiteral("接口返回错误：%1")
                        .arg(o["error"].toObject()["message"].toString());
                    return res;
                }
            }
            content = content.trimmed();
            if (content.isEmpty()) {
                res.error = QStringLiteral("返回内容为空");
            } else {
                res.ok = true;
                res.text = content;
                res.error.clear();
                return res;
            }
        } else if (status >= 400) {
            res.error = QStringLiteral("请求被拒绝（HTTP %1）：%2")
                .arg(status).arg(QString::fromUtf8(payload.left(200)));
            return res;
        }

        if (attempt < maxAttempts)
            QThread::msleep(attempt == 1 ? 1000 : 2000);
    }
    return res;
}
