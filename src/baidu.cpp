#include "baidu.h"
#include "managed.h"

#include <QBuffer>
#include <QCryptographicHash>
#include <QDateTime>
#include <QEventLoop>
#include <QHttpMultiPart>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QThread>
#include <QTimer>
#include <QUrlQuery>
#include <QRandomGenerator>

namespace {
QString md5Hex(const QByteArray& data) {
    return QString::fromLatin1(QCryptographicHash::hash(data, QCryptographicHash::Md5).toHex());
}
}

BaiduPictureTranslate::BaiduPictureTranslate(QObject* parent) : QObject(parent) {}

BaiduResult BaiduPictureTranslate::translate(const QImage& img, const QString& from,
                                             const QString& to, const QString& appId,
                                             const QString& secret, int paste, int timeoutMs) {
    BaiduResult res;
    if (img.isNull()) { res.error = QStringLiteral("图片为空"); return res; }
    // 托管模式：无用户凭据但内置了云代理 -> 签名在云端完成，客户端不发任何凭据
    const bool viaProxy = (appId.isEmpty() || secret.isEmpty()) && managed::available();
    if ((appId.isEmpty() || secret.isEmpty()) && !viaProxy) {
        res.error = QStringLiteral("未配置百度翻译 APPID / 密钥（设置 → 识别），且无内置云代理");
        return res;
    }

    // 上传编码：小图 PNG / 大图 JPG 压缩（托管链路走 base64 JSON，上限更紧）
    const QByteArray png = encodeImageForUpload(
        img, viaProxy ? 2500 * 1024 : 3900 * 1024);
    if (png.isEmpty()) {
        res.error = QStringLiteral("图片编码失败或过大，请缩小选区");
        return res;
    }

    const QString salt = QString::number(QDateTime::currentMSecsSinceEpoch());
    const QString cuid = QStringLiteral("APICUID");
    const QString mac = QStringLiteral("mac");
    const QString version = QStringLiteral("3");
    res.from = from;
    res.to = to;

    QUrl url;
    QUrlQuery q;
    if (viaProxy) {
        // 托管：只发业务参数，签名由云代理补齐
        url = QUrl(managed::endpoint(QStringLiteral("picture")));
        q.addQueryItem(QStringLiteral("from"), from);
        q.addQueryItem(QStringLiteral("to"), to);
        q.addQueryItem(QStringLiteral("paste"), QString::number(paste));
    } else {
        // sign = md5(appid + md5(image) + salt + cuid + mac + 密钥)
        const QString sign = md5Hex((appId + md5Hex(png) + salt + cuid + mac + secret).toUtf8());
        url = QUrl(qEnvironmentVariable("TACKSHOT_BAIDU_ENDPOINT",
                                        "https://fanyi-api.baidu.com/api/trans/sdk/picture"));
        q.addQueryItem(QStringLiteral("from"), from);
        q.addQueryItem(QStringLiteral("to"), to);
        q.addQueryItem(QStringLiteral("appid"), appId);
        q.addQueryItem(QStringLiteral("salt"), salt);
        q.addQueryItem(QStringLiteral("sign"), sign);
        q.addQueryItem(QStringLiteral("cuid"), cuid);
        q.addQueryItem(QStringLiteral("mac"), mac);
        q.addQueryItem(QStringLiteral("version"), version);
        q.addQueryItem(QStringLiteral("paste"), QString::number(paste));
    }
    url.setQuery(q);   // 1.8.1 修复：QUrlQuery 忘记挂回 URL，鉴权参数全部丢失 -> 52003

    QNetworkRequest req(url);
    req.setTransferTimeout(timeoutMs);
    req.setHeader(QNetworkRequest::UserAgentHeader, QStringLiteral("TackShot/1.9"));

    QNetworkAccessManager mgr;
    QNetworkReply* reply = nullptr;
    if (viaProxy) {
        // 托管：JSON + base64（部分网关对二进制 multipart 有损解码，必须走文本协议）
        QJsonObject jo;
        jo["image"] = QString::fromLatin1(png.toBase64());
        req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
        reply = mgr.post(req, QJsonDocument(jo).toJson(QJsonDocument::Compact));
    } else {
        auto* multi = new QHttpMultiPart(QHttpMultiPart::FormDataType);
        QHttpPart filePart;
        const bool isJpg = png.startsWith("\xFF\xD8\xFF");
        filePart.setHeader(QNetworkRequest::ContentTypeHeader,
                           isJpg ? QStringLiteral("image/jpeg") : QStringLiteral("image/png"));
        filePart.setHeader(QNetworkRequest::ContentDispositionHeader,
                           isJpg ? QStringLiteral("form-data; name=\"image\"; filename=\"tackshot.jpg\"")
                                 : QStringLiteral("form-data; name=\"image\"; filename=\"tackshot.png\""));
        filePart.setBody(png);
        multi->append(filePart);
        reply = mgr.post(req, multi);
        multi->setParent(reply);
    }

    QEventLoop loop;
    QTimer timer;
    timer.setSingleShot(true);
    timer.setInterval(timeoutMs);
    QObject::connect(&timer, &QTimer::timeout, &loop, [&]() {
        if (reply->isRunning()) reply->abort();
        loop.quit();
    });
    QObject::connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);
    timer.start();
    loop.exec();
    timer.stop();

    const QByteArray body = reply->readAll();
    res.errorCode = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
    const QNetworkReply::NetworkError netErr = reply->error();
    reply->deleteLater();

    if (netErr == QNetworkReply::OperationCanceledError) {
        res.error = QStringLiteral("请求超时（%1 秒）").arg(timeoutMs / 1000);
        return res;
    }
    if (netErr != QNetworkReply::NoError && body.isEmpty()) {
        res.error = QStringLiteral("网络错误：%1").arg(reply->errorString());
        return res;
    }

    QJsonParseError pe{};
    const QJsonDocument doc = QJsonDocument::fromJson(body, &pe);
    if (pe.error != QJsonParseError::NoError || !doc.isObject()) {
        res.error = QStringLiteral("返回格式无法解析");
        return res;
    }
    const QJsonObject o = doc.object();
    const QString codeStr = o.value(QStringLiteral("error_code")).toVariant().toString();
    const int code = codeStr.toInt();
    res.errorCode = code;
    if (code != 0) {
        const QString msg = o.value(QStringLiteral("error_msg")).toString();
        QString hint;
        switch (code) {
        case 52003: hint = QStringLiteral("APPID 未授权或服务未开通"); break;
        case 54001: hint = QStringLiteral("签名错误（检查密钥）"); break;
        case 54003: hint = QStringLiteral("访问频率受限"); break;
        case 54004: hint = QStringLiteral("账户余额不足"); break;
        case 58001: hint = QStringLiteral("译文语言方向不支持"); break;
        case 69005: hint = QStringLiteral("图片超过 4MB"); break;
        case 69006: hint = QStringLiteral("图片尺寸不符合要求"); break;
        case 69007: hint = QStringLiteral("图片格式不支持"); break;
        case 69004: hint = QStringLiteral("识别内容为空"); break;
        default: break;
        }
        res.error = QStringLiteral("百度翻译错误 %1：%2%3")
                        .arg(code).arg(msg,
                            hint.isEmpty() ? QString() : QStringLiteral("（%1）").arg(hint));
        return res;
    }

    const QJsonObject data = o.value(QStringLiteral("data")).toObject();
    res.from = data.value(QStringLiteral("from")).toString();
    res.to = data.value(QStringLiteral("to")).toString();
    res.sumSrc = data.value(QStringLiteral("sumSrc")).toString();
    res.sumDst = data.value(QStringLiteral("sumDst")).toString();

    for (const QJsonValue& v : data.value(QStringLiteral("content")).toArray()) {
        const QJsonObject c = v.toObject();
        BaiduLine line;
        line.src = c.value(QStringLiteral("src")).toString();
        line.dst = c.value(QStringLiteral("dst")).toString();
        const QStringList rc = c.value(QStringLiteral("rect")).toString().split(' ', Qt::SkipEmptyParts);
        if (rc.size() == 4)
            line.rect = QRect(rc[0].toInt(), rc[1].toInt(), rc[2].toInt(), rc[3].toInt());
        res.lines.append(line);
    }

    const QString pasteB64 = data.value(QStringLiteral("pasteImg")).toString();
    if (!pasteB64.isEmpty()) {
        QByteArray raw = QByteArray::fromBase64(pasteB64.toLatin1());
        res.pasteImage = QImage::fromData(raw);
    }

    res.ok = !res.lines.isEmpty() || !res.pasteImage.isNull();
    if (!res.ok) res.error = QStringLiteral("没有识别到文字");
    return res;
}

// ---------------- 文本翻译 ----------------

// 上传编码：小图 PNG 无损；大图 JPG 递降质量 + 缩放控制体积（识图上传提速 5~10 倍）
QByteArray encodeImageForUpload(const QImage& img, int maxBytes) {
    if (img.isNull()) return QByteArray();
    QImage conv = img;
    if (conv.width() > 4096 || conv.height() > 4096)
        conv = conv.scaled(4096, 4096, Qt::KeepAspectRatio, Qt::SmoothTransformation);
    for (int round = 0; round < 4; ++round) {
        QByteArray png;
        {
            QBuffer buf(&png);
            buf.open(QIODevice::WriteOnly);
            conv.save(&buf, "PNG");
        }
        if (png.size() <= 300 * 1024) return png;   // 小图无损最优
        for (int q : {85, 70, 55}) {
            QByteArray jpg;
            QBuffer buf(&jpg);
            buf.open(QIODevice::WriteOnly);
            if (conv.save(&buf, "JPG", q) && jpg.size() <= maxBytes) return jpg;
        }
        conv = conv.scaled(qRound(conv.width() * 0.75), qRound(conv.height() * 0.75),
                           Qt::KeepAspectRatio, Qt::SmoothTransformation);
    }
    return QByteArray();
}

// 中文语言名 -> 百度语言码（图片 / 文本翻译通用）
QString baiduLangCode(const QString& name) {
    const QString s = name.trimmed();
    if (s.isEmpty() || s.contains(QStringLiteral("自动"))) return QStringLiteral("auto");
    if (s.contains(QStringLiteral("英"))) return QStringLiteral("en");
    if (s.contains(QStringLiteral("日"))) return QStringLiteral("jp");
    if (s.contains(QStringLiteral("韩")) || s.contains(QStringLiteral("韓"))) return QStringLiteral("kor");
    if (s.contains(QStringLiteral("繁"))) return QStringLiteral("cht");
    if (s.contains(QStringLiteral("中"))) return QStringLiteral("zh");
    if (s.contains(QStringLiteral("法"))) return QStringLiteral("fra");
    if (s.contains(QStringLiteral("德"))) return QStringLiteral("de");
    if (s.contains(QStringLiteral("俄"))) return QStringLiteral("ru");
    if (s.contains(QStringLiteral("西"))) return QStringLiteral("spa");
    if (s.contains(QStringLiteral("葡"))) return QStringLiteral("pt");
    if (s.contains(QStringLiteral("意"))) return QStringLiteral("it");
    return QStringLiteral("auto");
}

BaiduTextTranslate::BaiduTextTranslate(QObject* parent) : QObject(parent) {}

namespace {

// 百度文本翻译错误码 -> 中文提示（返回空串表示该错误值得重试）
QString baiduTextErrorHint(int code, bool* retryable) {
    if (retryable) *retryable = false;
    switch (code) {
    case 52001: case 52002:
        if (retryable) *retryable = true;
        return QStringLiteral("请求超时/系统繁忙");
    case 52003: return QStringLiteral("APPID 未授权或未开通通用文本翻译");
    case 54001: return QStringLiteral("签名错误（检查密钥）");
    case 54003:
        if (retryable) *retryable = true;
        return QStringLiteral("访问频率受限（标准版 1 次/秒）");
    case 54004: return QStringLiteral("账户余额不足");
    case 54005: return QStringLiteral("长 query 请求频繁，请降低频率");
    case 58001: return QStringLiteral("译文语言方向不支持");
    case 58002: return QStringLiteral("服务已下线");
    case 90107: return QStringLiteral("认证失败，请注册百度账号");
    default: return QString();
    }
}

} // namespace

BaiduTextResult BaiduTextTranslate::translate(const QString& text, const QString& from,
                                              const QString& to, const QString& appId,
                                              const QString& secret, int timeoutMs) {
    BaiduTextResult res;
    if (text.trimmed().isEmpty()) { res.error = QStringLiteral("没有可翻译的内容"); return res; }
    // 托管模式：无凭据但有内置云代理 -> 签名在云端完成
    const bool viaProxy = (appId.isEmpty() || secret.isEmpty()) && managed::available();
    if ((appId.isEmpty() || secret.isEmpty()) && !viaProxy) {
        res.error = QStringLiteral("未配置百度翻译 APPID / 密钥（设置 → 识别），且无内置云代理");
        return res;
    }

    const QString directEndpoint = qEnvironmentVariable(
        "TACKSHOT_BAIDU_TEXT_ENDPOINT", "https://fanyi-api.baidu.com/api/trans/vip/translate");

    // 54003（限流）/ 52001/52002（超时/繁忙）自动等待重试，标准版 QPS=1
    const int maxAttempts = 3;
    for (int attempt = 1; attempt <= maxAttempts; ++attempt) {
        const QString salt = QString::number(QDateTime::currentMSecsSinceEpoch());

        QUrlQuery q;
        q.addQueryItem(QStringLiteral("q"), text);
        q.addQueryItem(QStringLiteral("from"), from);
        q.addQueryItem(QStringLiteral("to"), to);
        QString endpoint;
        if (viaProxy) {
            endpoint = managed::endpoint(QStringLiteral("text"));
        } else {
            // sign = md5(appid + q + salt + 密钥)，q 为原文 UTF-8（不做 URL 编码）
            const QString sign = md5Hex((appId + text + salt + secret).toUtf8());
            q.addQueryItem(QStringLiteral("appid"), appId);
            q.addQueryItem(QStringLiteral("salt"), salt);
            q.addQueryItem(QStringLiteral("sign"), sign);
            endpoint = directEndpoint;
        }

        QNetworkRequest req{QUrl(endpoint)};
        req.setHeader(QNetworkRequest::ContentTypeHeader,
                      QStringLiteral("application/x-www-form-urlencoded"));
        req.setTransferTimeout(timeoutMs);
        req.setHeader(QNetworkRequest::UserAgentHeader, QStringLiteral("TackShot/1.8"));

        QNetworkAccessManager mgr;
        QNetworkReply* reply = mgr.post(req, q.toString(QUrl::FullyEncoded).toUtf8());

        QEventLoop loop;
        QTimer timer;
        timer.setSingleShot(true);
        timer.setInterval(timeoutMs);
        bool timedOut = false;
        QObject::connect(&timer, &QTimer::timeout, &loop, [&]() {
            timedOut = true;
            if (reply->isRunning()) reply->abort();
            loop.quit();
        });
        QObject::connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);
        timer.start();
        loop.exec();
        timer.stop();

        const QByteArray body = reply->readAll();
        const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QNetworkReply::NetworkError netErr = reply->error();
        const QString nerr = reply->errorString();
        reply->deleteLater();

        if (timedOut || netErr == QNetworkReply::OperationCanceledError) {
            res.error = QStringLiteral("请求超时（%1 秒）").arg(timeoutMs / 1000);
            if (attempt < maxAttempts) { QThread::msleep(1100); continue; }
            return res;
        }
        if (status == 0 || (netErr != QNetworkReply::NoError && body.isEmpty())) {
            res.error = QStringLiteral("网络错误：%1").arg(nerr);
            return res;
        }

        QJsonParseError pe{};
        const QJsonDocument doc = QJsonDocument::fromJson(body, &pe);
        if (pe.error != QJsonParseError::NoError || !doc.isObject()) {
            res.error = QStringLiteral("返回格式无法解析");
            return res;
        }
        const QJsonObject o = doc.object();
        const int code = o.value(QStringLiteral("error_code")).toVariant().toString().toInt();
        if (code != 0) {
            res.errorCode = code;
            const QString msg = o.value(QStringLiteral("error_msg")).toString();
            bool retryable = false;
            const QString hint = baiduTextErrorHint(code, &retryable);
            res.error = QStringLiteral("百度翻译错误 %1：%2%3")
                            .arg(code).arg(msg,
                                hint.isEmpty() ? QString() : QStringLiteral("（%1）").arg(hint));
            if (retryable && attempt < maxAttempts) { QThread::msleep(1100); continue; }
            return res;
        }

        res.from = o.value(QStringLiteral("from")).toString();
        res.to = o.value(QStringLiteral("to")).toString();
        QStringList dst;
        for (const QJsonValue& v : o.value(QStringLiteral("trans_result")).toArray()) {
            const QJsonObject item = v.toObject();
            dst << item.value(QStringLiteral("dst")).toString();
        }
        if (dst.isEmpty()) { res.error = QStringLiteral("返回译文为空"); return res; }
        res.text = dst.join(QLatin1Char('\n'));
        res.ok = true;
        return res;
    }
    return res;
}
