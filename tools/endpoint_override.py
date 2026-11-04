import io

# Baidu：支持环境变量覆盖端点（测试用）
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\baidu.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace('    QUrl url(QStringLiteral("https://fanyi-api.baidu.com/api/trans/sdk/picture"));',
'''    QString endpoint = qEnvironmentVariable("TACKSHOT_BAIDU_ENDPOINT",
                                            "https://fanyi-api.baidu.com/api/trans/sdk/picture");
    QUrl url(endpoint);''')
io.open(p, "w", encoding="utf-8").write(s)

# SimpleTex：同样支持覆盖
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\simpletex.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace('''    const QString url = light ? QStringLiteral("https://server.simpletex.cn/api/latex_ocr_turbo")
                              : QStringLiteral("https://server.simpletex.cn/api/latex_ocr");''',
'''    QString url = light ? QStringLiteral("https://server.simpletex.cn/api/latex_ocr_turbo")
                        : QStringLiteral("https://server.simpletex.cn/api/latex_ocr");
    const QString override = qEnvironmentVariable("TACKSHOT_SIMPLETEX_ENDPOINT");
    if (!override.isEmpty()) url = override;''')
io.open(p, "w", encoding="utf-8").write(s)
print("endpoint overrides added")
