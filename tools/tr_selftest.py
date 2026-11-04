import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace('#include "audiocap.h"', '#include "audiocap.h"\n#include "translate.h"\n#include "secrets.h"')

anchor = "    // DPI 自检：逐屏校验"
code = '''    // 翻译自检：针对 mock 服务验证 正常 / 401 / 429 重试
    int trIdx = args.indexOf("--translate-selftest");
    if (trIdx >= 0) {
        QString base = (trIdx + 1 < args.size()) ? args[trIdx + 1] : "http://127.0.0.1:8899/v1";
        QString out = (trIdx + 2 < args.size()) ? args[trIdx + 2] : base + "_report.txt";

        ProviderPreset p;
        p.id = "mock";
        p.model = "deepseek-flash";
        TranslateClient client;
        QStringList log;
        bool allPass = true;

        // 1) 正常
        p.baseUrl = base + "/ok";
        auto r1 = client.translate(QStringLiteral("Hello, world"), QStringLiteral("简体中文"), p, "sk-test");
        bool p1 = r1.ok && !r1.text.isEmpty() && r1.attempts == 1;
        log << QString("normal: ok=%1 attempts=%2 text=%3 pass=%4")
                   .arg(r1.ok).arg(r1.attempts).arg(r1.text.left(20)).arg(p1);
        allPass &= p1;

        // 2) 401 不重试
        p.baseUrl = base + "/bad";
        auto r2 = client.translate(QStringLiteral("hello"), QStringLiteral("简体中文"), p, "sk-bad");
        bool p2 = !r2.ok && r2.httpStatus == 401 && r2.attempts == 1;
        log << QString("auth401: ok=%1 status=%2 attempts=%3 err=%4 pass=%5")
                   .arg(r2.ok).arg(r2.httpStatus).arg(r2.attempts).arg(r2.error).arg(p2);
        allPass &= p2;

        // 3) 429 重试到成功
        p.baseUrl = base + "/flaky";
        auto r3 = client.translate(QStringLiteral("hello"), QStringLiteral("简体中文"), p, "sk-test");
        bool p3 = r3.ok && r3.attempts == 3;
        log << QString("retry429: ok=%1 attempts=%2 text=%3 pass=%4")
                   .arg(r3.ok).arg(r3.attempts).arg(r3.text.left(20)).arg(p3);
        allPass &= p3;

        log << QString("ALL_PASS=%1").arg(allPass ? "true" : "false");
        QFile rf(out);
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts.setEncoding(QStringConverter::Utf8);
            for (const auto& l : log) ts << l << "\\n";
            rf.close();
        }
        return allPass ? 0 : 13;
    }

    // DPI 自检：逐屏校验'''
if anchor in s:
    s = s.replace(anchor, code, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("translate selftest added")
