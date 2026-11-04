import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\translate.cpp"
s = io.open(p, encoding="utf-8").read()
old = """TranslateResult TranslateClient::doRequest(const QString& text, const QString& targetLang,
                                           const ProviderPreset& p, const QString& apiKey,
                                           int timeoutMs, bool allowRetry, const QString& glossary) {"""
new = """TranslateResult TranslateClient::doRequest(const QString& text, const QString& targetLang,
                                           const ProviderPreset& p, const QString& apiKey,
                                           int timeoutMs, bool allowRetry, const QString& glossary,
                                           const QString& sourceLang) {"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("doRequest fixed")
else:
    print("MISS")
