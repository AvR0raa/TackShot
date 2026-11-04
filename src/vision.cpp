#include "vision.h"

#include <QBuffer>
#include <QEventLoop>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QThread>
#include <QTimer>
#include <QUrl>

namespace {

// 长边上限：再大对识别精度几乎无益，只会拖慢编码与上传
constexpr int kMaxImageSide = 1600;
// 429 / 5xx 最多重试 2 次（合计 3 次请求）
constexpr int kMaxAttempts = 3;

QString defaultPrompt() {
    return QStringLiteral("请识别这张截图中的主要内容，用简体中文简洁说明。");
}

// baseUrl 去掉末尾斜杠后拼 /chat/completions；已带该后缀则不重复拼
QString buildEndpoint(const QString& baseUrl) {
    QString u = baseUrl.trimmed();
    while (u.endsWith(QLatin1Char('/'))) u.chop(1);
    if (u.isEmpty()) return QString();
    if (u.endsWith(QStringLiteral("/chat/completions"))) return u;
    return u + QStringLiteral("/chat/completions");
}

// 图片长边缩到 <= 1600，再编码为 PNG（走内置 PNG 编解码，不依赖插件）
bool encodePng(const QImage& img, QByteArray* png) {
    QImage out = img;
    if (out.width() > kMaxImageSide || out.height() > kMaxImageSide) {
        out = out.scaled(kMaxImageSide, kMaxImageSide,
                         Qt::KeepAspectRatio, Qt::SmoothTransformation);
    }
    QBuffer buf(png);
    if (!buf.open(QIODevice::WriteOnly)) return false;
    if (!out.save(&buf, "PNG")) return false;
    buf.close();
    return !png->isEmpty();
}

// 只取返回体开头一小段，避免把整页 HTML 回显进提示
QString briefBody(const QByteArray& body) {
    const QString s = QString::fromUtf8(body.left(200)).simplified();
    if (s.isEmpty()) return QStringLiteral("（无返回内容）");
    return s;
}

// choices[0].message.content：可能是字符串，也可能是分段数组（拼接各元素 text）
QString contentToText(const QJsonValue& v) {
    if (v.isString()) return v.toString();
    if (v.isArray()) {
        QString out;
        for (const QJsonValue& item : v.toArray()) {
            if (item.isString()) {
                out += item.toString();
                continue;
            }
            if (!item.isObject()) continue;
            const QJsonObject o = item.toObject();
            const QString t = o.value(QStringLiteral("text")).toString();
            if (!t.isEmpty()) out += t;
        }
        return out;
    }
    if (v.isObject()) {
        const QJsonObject o = v.toObject();
        const QString t = o.value(QStringLiteral("text")).toString();
        if (!t.isEmpty()) return t;
        return o.value(QStringLiteral("content")).toString();
    }
    return QString();
}

} // namespace

VisionClient::VisionClient(QObject* parent) : QObject(parent) {}

VisionResult VisionClient::recognize(const QImage& img, const QString& prompt,
                                     const QString& baseUrl, const QString& model,
                                     const QString& apiKey, int timeoutMs) {
    return doRequest(img, prompt, baseUrl, model, apiKey, timeoutMs, true, false);
}

VisionResult VisionClient::probe(const QString& baseUrl, const QString& model,
                                 const QString& apiKey) {
    // 用一张 64x64 纯白小图探活：成本最低，又能验证视觉通道确实可用
    QImage tiny(64, 64, QImage::Format_RGB32);
    tiny.fill(Qt::white);
    return doRequest(tiny, QStringLiteral("ping"), baseUrl, model, apiKey, 20000, false, true);
}

VisionResult VisionClient::doRequest(const QImage& img, const QString& prompt,
                                     const QString& baseUrl, const QString& model,
                                     const QString& apiKey, int timeoutMs,
                                     bool allowRetry, bool allowEmpty) {
    VisionResult res;
    res.model = model;

    if (img.isNull()) {
        res.error = QStringLiteral("图片为空，无法识别");
        return res;
    }
    const QString endpoint = buildEndpoint(baseUrl);
    if (endpoint.isEmpty()) {
        res.error = QStringLiteral("接口地址为空，请先填写 baseUrl");
        return res;
    }
    if (timeoutMs <= 0) timeoutMs = 60000;

    QByteArray png;
    if (!encodePng(img, &png)) {
        res.error = QStringLiteral("图片编码失败（PNG）");
        return res;
    }

    // 视觉请求体：messages[0].content 为 [文本段, 图片段]
    QJsonObject textPart;
    textPart[QStringLiteral("type")] = QStringLiteral("text");
    textPart[QStringLiteral("text")] =
        prompt.trimmed().isEmpty() ? defaultPrompt() : prompt.trimmed();

    QJsonObject imageUrl;
    imageUrl[QStringLiteral("url")] =
        QStringLiteral("data:image/png;base64,") + QString::fromLatin1(png.toBase64());

    QJsonObject imagePart;
    imagePart[QStringLiteral("type")] = QStringLiteral("image_url");
    imagePart[QStringLiteral("image_url")] = imageUrl;

    QJsonArray content;
    content.append(textPart);
    content.append(imagePart);

    QJsonObject user;
    user[QStringLiteral("role")] = QStringLiteral("user");
    user[QStringLiteral("content")] = content;

    QJsonArray messages;
    messages.append(user);

    QJsonObject body;
    body[QStringLiteral("model")] = model;
    body[QStringLiteral("messages")] = messages;
    body[QStringLiteral("temperature")] = 0;
    body[QStringLiteral("stream")] = false;

    const QByteArray payload = QJsonDocument(body).toJson(QJsonDocument::Compact);
    const int maxAttempts = allowRetry ? kMaxAttempts : 1;

    for (int attempt = 1; attempt <= maxAttempts; ++attempt) {
        QNetworkAccessManager mgr; // 每次请求独立，避免沿用上一条连接的残留状态
        QNetworkRequest req{QUrl(endpoint)};
        req.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));
        if (!apiKey.isEmpty())
            req.setRawHeader("Authorization", ("Bearer " + apiKey).toUtf8());
        req.setRawHeader("User-Agent", "TackShot/1.8");
        req.setTransferTimeout(timeoutMs);

        QNetworkReply* reply = mgr.post(req, payload);

        QEventLoop loop;
        QTimer timer;
        timer.setSingleShot(true);
        bool timedOut = false;
        QObject::connect(&timer, &QTimer::timeout, [&]() {
            timedOut = true;
            reply->abort();
        });
        QObject::connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);
        timer.start(timeoutMs);
        loop.exec();
        timer.stop();

        const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        // 已 abort 的 reply 设备已关闭，此时再 readAll 会刷 QIODevice 警告
        QByteArray data;
        if (!timedOut && reply->isOpen()) data = reply->readAll();
        const QString netErr = reply->errorString();
        reply->deleteLater();
        res.httpStatus = status;

        if (timedOut) {
            res.error = QStringLiteral("请求超时（%1 秒）").arg(timeoutMs / 1000);
            return res; // 超时不重试，避免用户长时间干等
        }
        if (status == 0) {
            res.error = QStringLiteral("网络错误：%1").arg(netErr);
            return res;
        }
        // 以下三种属于配置/账户问题，重试没有意义，直接返回
        if (status == 401 || status == 403) {
            res.error = QStringLiteral("API Key 无效或无权限（HTTP %1）").arg(status);
            return res;
        }
        if (status == 402) {
            res.error = QStringLiteral("余额不足（HTTP 402）");
            return res;
        }
        // 限流与服务端错误：退避 1s、2s 后重试
        if (status == 429 || status >= 500) {
            res.error = (status == 429)
                ? QStringLiteral("请求过于频繁（HTTP 429）")
                : QStringLiteral("服务端错误（HTTP %1）").arg(status);
            if (attempt < maxAttempts) {
                QThread::msleep(attempt == 1 ? 1000 : 2000);
                continue;
            }
            return res;
        }
        if (status == 200) {
            const QJsonDocument doc = QJsonDocument::fromJson(data);
            if (!doc.isObject()) {
                res.error = QStringLiteral("返回格式无法解析（不是 JSON）：%1").arg(briefBody(data));
                return res;
            }
            const QJsonObject o = doc.object();
            if (o.contains(QStringLiteral("error"))) {
                const QJsonObject e = o.value(QStringLiteral("error")).toObject();
                QString msg = e.value(QStringLiteral("message")).toString();
                if (msg.isEmpty()) msg = briefBody(data);
                res.error = QStringLiteral("接口返回错误：%1").arg(msg);
                return res;
            }
            QString text;
            const QJsonArray choices = o.value(QStringLiteral("choices")).toArray();
            if (!choices.isEmpty()) {
                const QJsonObject msg = choices.at(0).toObject()
                                            .value(QStringLiteral("message")).toObject();
                text = contentToText(msg.value(QStringLiteral("content"))).trimmed();
            }
            if (text.isEmpty() && !allowEmpty) {
                res.error = QStringLiteral("返回内容为空（模型可能不支持图片输入）");
                return res;
            }
            res.ok = true;
            res.text = text;
            res.error.clear();
            return res;
        }
        if (status == 404) {
            res.error = QStringLiteral("接口地址不存在（HTTP 404）：%1").arg(briefBody(data));
            return res;
        }
        if (status >= 400) {
            res.error = QStringLiteral("请求被拒绝（HTTP %1）：%2")
                            .arg(status).arg(briefBody(data));
            return res;
        }
        res.error = QStringLiteral("意外的返回状态（HTTP %1）").arg(status);
        return res;
    }
    return res;
}
