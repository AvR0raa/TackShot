import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
anchor = "    // 翻译自检：针对 mock 服务验证 正常 / 401 / 429 重试"
code = '''    // 密钥存储自检：DPAPI 加密写入 -> 读回 -> 删除
    int secIdx = args.indexOf("--secret-selftest");
    if (secIdx >= 0) {
        QString out = (secIdx + 1 < args.size()) ? args[secIdx + 1] : "secret.txt";
        const QString probeName = "selftest_probe";
        const QString value = QStringLiteral("sk-测试-1234567890");
        bool saved = secrets::save(probeName, value);
        QString back = secrets::load(probeName);
        bool same = (back == value);
        QFile f(secrets::storePath());
        bool exists = f.exists();
        QByteArray raw;
        if (f.open(QIODevice::ReadOnly)) { raw = f.readAll(); f.close(); }
        bool plainVisible = raw.contains(value.toUtf8());
        secrets::remove(probeName);

        bool pass = saved && same && exists && !plainVisible;
        QFile rf(out);
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts.setEncoding(QStringConverter::Utf8);
            ts << "saved=" << saved << " roundtrip=" << same
               << " plaintextInFile=" << plainVisible << "\\n";
            ts << "storeSize=" << raw.size() << " pass=" << (pass ? "true" : "false") << "\\n";
            rf.close();
        }
        return pass ? 0 : 14;
    }

'''
if anchor in s:
    s = s.replace(anchor, code + anchor, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("secret selftest added")
else:
    print("MISS")
