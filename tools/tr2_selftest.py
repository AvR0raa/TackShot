import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()

start = s.index("    // 翻译自检：针对 mock 服务验证 正常 / 401 / 429 重试")
end = s.index("    // DPI 自检：逐屏校验")
new = r'''    // 翻译自检：正常 / 401 / 429 重试 / 分块 / 缓存 / 术语表 / 降级
    int trIdx = args.indexOf("--translate-selftest");
    if (trIdx >= 0) {
        QString base = (trIdx + 1 < args.size()) ? args[trIdx + 1] : "http://127.0.0.1:8899/v1";
        QString out = (trIdx + 2 < args.size()) ? args[trIdx + 2] : base + "_report.txt";

        auto mockRequests = [&]() -> int {
            QNetworkAccessManager mgr;
            QNetworkRequest req{QUrl("http://127.0.0.1:8899/stats")};
            req.setTransferTimeout(5000);
            QNetworkReply* rp = mgr.get(req);
            QEventLoop loop;
            QObject::connect(rp, &QNetworkReply::finished, &loop, &QEventLoop::quit);
            loop.exec();
            QByteArray body = rp->readAll();
            rp->deleteLater();
            auto doc = QJsonDocument::fromJson(body);
            return doc.object()["requests"].toInt();
        };

        ProviderPreset p;
        p.id = "mock";
        p.model = "deepseek-flash";
        TranslateClient client;
        QStringList log;
        bool allPass = true;

        // 1) 正常
        p.baseUrl = base + "/ok";
        auto r1 = client.translateLong(QStringLiteral("Hello, world"), QStringLiteral("简体中文"),
                                       p, "sk-test", QString(), 1500, false);
        bool p1 = r1.ok && !r1.text.isEmpty() && r1.chunkCount == 1;
        log << QString("normal: ok=%1 chunks=%2 text=%3 pass=%4")
                   .arg(r1.ok).arg(r1.chunkCount).arg(r1.text.left(16)).arg(p1);
        allPass &= p1;

        // 2) 401 不重试
        p.baseUrl = base + "/bad";
        auto r2 = client.translateLong(QStringLiteral("hello"), QStringLiteral("简体中文"),
                                       p, "sk-bad", QString(), 1500, false);
        bool p2 = !r2.ok && r2.chunkFailed == 1;
        log << QString("auth401: ok=%1 chunkFailed=%2 err=%3 pass=%4")
                   .arg(r2.ok).arg(r2.chunkFailed).arg(r2.error.left(24)).arg(p2);
        allPass &= p2;

        // 3) 429 重试到成功
        p.baseUrl = base + "/flaky";
        auto r3 = client.translateLong(QStringLiteral("hello"), QStringLiteral("简体中文"),
                                       p, "sk-test", QString(), 1500, false);
        bool p3 = r3.ok;
        log << QString("retry429: ok=%1 text=%2 pass=%3")
                   .arg(r3.ok).arg(r3.text.left(16)).arg(p3);
        allPass &= p3;

        // 4) 分块：40 段 x 40 字，chunk=500 -> 至少 3 块
        p.baseUrl = base + "/ok";
        QStringList paras;
        for (int i = 0; i < 40; ++i)
            paras << QString("第%1段：这是一段用于测试分块的中文文本，长度大约四十个字符左右。").arg(i + 1);
        QString longText = paras.join("\n");
        int before = mockRequests();
        auto r4 = client.translateLong(longText, QStringLiteral("简体中文"), p, "sk-test",
                                       QString(), 500, false);
        int after = mockRequests();
        bool p4 = r4.ok && r4.chunkCount >= 3 && (after - before) == r4.chunkCount;
        log << QString("chunk: ok=%1 chunks=%2 requests=%3 pass=%4")
                   .arg(r4.ok).arg(r4.chunkCount).arg(after - before).arg(p4);
        allPass &= p4;

        // 5) 缓存：同一段再翻一次，不应产生新请求
        int before2 = mockRequests();
        auto r5 = client.translateLong(QStringLiteral("Hello, world"), QStringLiteral("简体中文"),
                                       p, "sk-test", QString(), 1500, true);
        int after2 = mockRequests();
        bool p5 = r5.ok && r5.fromCache && (after2 == before2) && r5.text == r1.text;
        log << QString("cache: ok=%1 fromCache=%2 newRequests=%3 pass=%4")
                   .arg(r5.ok).arg(r5.fromCache).arg(after2 - before2).arg(p5);
        allPass &= p5;

        // 6) 术语表：mock 在 system 里看到“术语表”会回 GLOSSARY_OK 前缀
        auto r6 = client.translateLong(QStringLiteral("TackShot is great"), QStringLiteral("简体中文"),
                                       p, "sk-test", QStringLiteral("TackShot=塔克肖特"), 1500, false);
        bool p6 = r6.ok && r6.text.contains("GLOSSARY_OK");
        log << QString("glossary: ok=%1 marker=%2 pass=%3")
                   .arg(r6.ok).arg(r6.text.left(14)).arg(p6);
        allPass &= p6;

        // 7) 降级：主引擎 401 -> 备用引擎成功
        ProviderPreset bad = p; bad.id = "primary"; bad.baseUrl = base + "/bad";
        ProviderPreset good = p; good.id = "backup"; good.baseUrl = base + "/ok";
        auto ra = client.translateLong(QStringLiteral("hello"), QStringLiteral("简体中文"),
                                       bad, "sk-bad", QString(), 1500, false);
        auto rb = client.translateLong(QStringLiteral("hello"), QStringLiteral("简体中文"),
                                       good, "sk-ok", QString(), 1500, false);
        bool p7 = !ra.ok && rb.ok;
        log << QString("fallback: primaryOk=%1 backupOk=%2 pass=%3")
                   .arg(ra.ok).arg(rb.ok).arg(p7);
        allPass &= p7;

        log << QString("ALL_PASS=%1").arg(allPass ? "true" : "false");
        QFile rf(out);
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts.setEncoding(QStringConverter::Utf8);
            for (const auto& l : log) ts << l << "\n";
            rf.close();
        }
        return allPass ? 0 : 13;
    }

'''
s = s[:start] + new + s[end:]
s = s.replace('#include "translate.h"', '#include "translate.h"\n#include <QNetworkAccessManager>\n#include <QNetworkReply>\n#include <QEventLoop>\n#include <QJsonDocument>\n#include <QJsonObject>')
io.open(p, "w", encoding="utf-8").write(s)
print("selftest extended")
