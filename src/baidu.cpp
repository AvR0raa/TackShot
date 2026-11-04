#include "baidu.h"

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
    if (appId.isEmpty() || secret.isEmpty()) {
        res.error = QStringLiteral("未配置百度翻译 APPID / 密钥");
        return res;
    }

    QByteArray png;
    {
        QImage conv = img;
        // 百度要求 png/jpg，最短边 >=30，最长边 <=4096，大小 <=4M
        if (conv.width() > 4096 || conv.height() > 4096)
            conv = conv.scaled(4096, 4096, Qt::KeepAspectRatio, Qt::SmoothTransformation);
        QBuffer buf(&png);
        buf.open(QIODevice::WriteOnly);
        conv.save(&buf, "PNG");
    }
    if (png.size() > 4 * 1024 * 1024) {
        res.error = QStringLiteral("图片超过 4MB，请缩小选区");
        return res;
    }

    const QString salt = QString::number(QDateTime::currentMSecsSinceEpoch());
    const QString cuid = QStringLiteral("APICUID");
    const QString mac = QStringLiteral("mac");
    const QString version = QStringLiteral("3");
    res.from = from;
    res.to = to;

    // sign = md5(appid + md5(image) + salt + cuid + mac + 密钥)
    const QString sign = md5Hex((appId + md5Hex(png) + salt + cuid + mac + secret).toUtf8());

    QString endpoint = qEnvironmentVariable("TACKSHOT_BAIDU_ENDPOINT",
                                            "https://fanyi-api.baidu.com/api/trans/sdk/picture");
    QUrl url(endpoint);
    QUrlQuery q;
    q.addQueryItem(QStringLiteral("from"), from);
    q.addQueryItem(QStringLiteral("to"), to);
    q.addQueryItem(QStringLiteral("appid"), appId);
    q.addQueryItem(QStringLiteral("salt"), salt);
    q.addQueryItem(QStringLiteral("sign"), sign);
    q.addQueryItem(QStringLiteral("cuid"), cuid);
    q.addQueryItem(QStringLiteral("mac"), mac);
    q.addQueryItem(QStringLiteral("version"), version);
    q.addQueryItem(QStringLiteral("paste"), QString::number(paste));

    auto* multi = new QHttpMultiPart(QHttpMultiPart::FormDataType);
    QHttpPart filePart;
    filePart.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("image/png"));
    filePart.setHeader(QNetworkRequest::ContentDispositionHeader,
                       QStringLiteral("form-data; name=\"image\"; filename=\"tackshot.png\""));
    filePart.setBody(png);
    multi->append(filePart);

    QNetworkRequest req(url);
    req.setTransferTimeout(timeoutMs);
    req.setHeader(QNetworkRequest::UserAgentHeader, QStringLiteral("TackShot/1.7"));

    QNetworkAccessManager mgr;
    QNetworkReply* reply = mgr.post(req, multi);
    multi->setParent(reply);

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
