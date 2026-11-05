#include "simpletex.h"
#include "managed.h"
#include "baidu.h"

#include <QBuffer>
#include <QEventLoop>
#include <QHttpMultiPart>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QTimer>

SimpleTexClient::SimpleTexClient(QObject* parent) : QObject(parent) {}

SimpleTexResult SimpleTexClient::recognize(const QImage& img, const QString& token,
                                           bool light, int timeoutMs) {
    SimpleTexResult res;
    if (img.isNull()) { res.error = QStringLiteral("图片为空"); return res; }
    // 托管模式：无用户 Token 但内置了云代理 -> Token 由云端补齐
    const bool viaProxy = token.trimmed().isEmpty() && managed::available();
    if (token.trimmed().isEmpty() && !viaProxy) {
        res.error = QStringLiteral("未配置 SimpleTex Token（设置 → 识别），且无内置云代理");
        return res;
    }

    // SimpleTex 建议最长边 <=2048；小图 PNG 无损 / 大图 JPG 压缩（上传提速）
    QImage conv = img;
    if (conv.width() > 2048 || conv.height() > 2048)
        conv = conv.scaled(2048, 2048, Qt::KeepAspectRatio, Qt::SmoothTransformation);
    const QByteArray png = encodeImageForUpload(conv, 2000 * 1024);
    if (png.isEmpty()) { res.error = QStringLiteral("图片编码失败"); return res; }

    QString url = light ? QStringLiteral("https://server.simpletex.cn/api/latex_ocr_turbo")
                        : QStringLiteral("https://server.simpletex.cn/api/latex_ocr");
    const QString override = qEnvironmentVariable("TACKSHOT_SIMPLETEX_ENDPOINT");
    if (!override.isEmpty()) url = override;
    if (viaProxy)
        url = managed::endpoint(QStringLiteral("simpletex"))
              + (light ? QStringLiteral("?light=1") : QStringLiteral("?light=0"));

    QNetworkRequest req{QUrl(url)};
    req.setTransferTimeout(timeoutMs);
    if (!viaProxy)   // 托管：Token 由云代理补齐，客户端不发
        req.setRawHeader("token", token.trimmed().toUtf8());
    req.setHeader(QNetworkRequest::UserAgentHeader, QStringLiteral("TackShot/1.9"));

    QNetworkAccessManager mgr;
    QNetworkReply* reply = nullptr;
    if (viaProxy) {
        // 托管：JSON + base64（网关对二进制 multipart 有损解码）
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
                           isJpg ? QStringLiteral("form-data; name=\"file\"; filename=\"tackshot.jpg\"")
                                 : QStringLiteral("form-data; name=\"file\"; filename=\"tackshot.png\""));
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
    res.httpStatus = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
    const QNetworkReply::NetworkError netErr = reply->error();
    const QString netStr = reply->errorString();
    reply->deleteLater();

    if (netErr == QNetworkReply::OperationCanceledError) {
        res.error = QStringLiteral("请求超时（%1 秒）").arg(timeoutMs / 1000);
        return res;
    }
    if (res.httpStatus == 401 || res.httpStatus == 403) {
        res.error = QStringLiteral("Token 无效或无权限（HTTP %1）").arg(res.httpStatus);
        return res;
    }
    if (netErr != QNetworkReply::NoError && body.isEmpty()) {
        res.error = QStringLiteral("网络错误：%1").arg(netStr);
        return res;
    }

    QJsonParseError pe{};
    const QJsonDocument doc = QJsonDocument::fromJson(body, &pe);
    if (pe.error != QJsonParseError::NoError || !doc.isObject()) {
        res.error = QStringLiteral("返回格式无法解析（HTTP %1）").arg(res.httpStatus);
        return res;
    }

    const QJsonObject o = doc.object();
    if (!o.value(QStringLiteral("status")).toBool()) {
        QString msg = o.value(QStringLiteral("message")).toString();
        if (msg.isEmpty()) msg = o.value(QStringLiteral("msg")).toString();
        res.error = msg.isEmpty() ? QStringLiteral("识别失败（HTTP %1）").arg(res.httpStatus) : msg;
        return res;
    }

    const QJsonObject r = o.value(QStringLiteral("res")).toObject();
    res.latex = r.value(QStringLiteral("latex")).toString().trimmed();
    res.confidence = r.value(QStringLiteral("conf")).toDouble();
    res.ok = !res.latex.isEmpty();
    if (!res.ok) res.error = QStringLiteral("没有识别到公式");
    return res;
}
