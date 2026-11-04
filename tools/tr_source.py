import io

# ---------------- translate.h：加 sourceLang 参数 ----------------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\translate.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("""    TranslateResult translateLong(const QString& text, const QString& targetLang,
                                  const ProviderPreset& p, const QString& apiKey,
                                  const QString& glossary = QString(),
                                  int chunkChars = 1500,
                                  bool useCache = true);""",
"""    TranslateResult translateLong(const QString& text, const QString& targetLang,
                                  const ProviderPreset& p, const QString& apiKey,
                                  const QString& glossary = QString(),
                                  int chunkChars = 1500,
                                  bool useCache = true,
                                  const QString& sourceLang = QString());""")
s = s.replace("""    TranslateResult translateLine(const QString& text, const QString& targetLang,
                                  const ProviderPreset& p, const QString& apiKey,
                                  const QString& glossary = QString());""",
"""    TranslateResult translateLine(const QString& text, const QString& targetLang,
                                  const ProviderPreset& p, const QString& apiKey,
                                  const QString& glossary = QString(),
                                  const QString& sourceLang = QString());""")
s = s.replace("""    TranslateResult doRequest(const QString& text, const QString& targetLang,
                              const ProviderPreset& p, const QString& apiKey,
                              int timeoutMs, bool allowRetry, const QString& glossary = QString());
    QString buildPrompt(const QString& targetLang, const QString& glossary) const;""",
"""    TranslateResult doRequest(const QString& text, const QString& targetLang,
                              const ProviderPreset& p, const QString& apiKey,
                              int timeoutMs, bool allowRetry, const QString& glossary = QString(),
                              const QString& sourceLang = QString());
    QString buildPrompt(const QString& targetLang, const QString& glossary,
                        const QString& sourceLang = QString()) const;""")
io.open(p, "w", encoding="utf-8").write(s)

# ---------------- translate.cpp ----------------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\translate.cpp"
s = io.open(p, encoding="utf-8").read()

s = s.replace("""QString TranslateClient::buildPrompt(const QString& targetLang, const QString& glossary) const {
    QString s = QStringLiteral(
        "你是专业翻译引擎。把用户提供的文本翻译成%1。\\n"
        "规则：\\n"
        "1) 只输出译文，不要解释、不要加引号、不要输出原文；\\n"
        "2) 保留段落、换行、列表编号与缩进；\\n"
        "3) 代码、URL、邮箱、数字、专有名词原样保留；\\n"
        "4) 如果原文已经是目标语言，原样返回。").arg(targetLang);""",
"""QString TranslateClient::buildPrompt(const QString& targetLang, const QString& glossary,
                                     const QString& sourceLang) const {
    const bool autoDetect = sourceLang.trimmed().isEmpty() ||
                            sourceLang.contains(QStringLiteral("自动"));
    QString head;
    if (autoDetect)
        head = QStringLiteral("你是专业翻译引擎。判断用户文本的语言，并翻译成%1。\\n").arg(targetLang);
    else
        head = QStringLiteral("你是专业翻译引擎。把用户提供的%1文本翻译成%2。\\n")
                   .arg(sourceLang, targetLang);
    QString s = head + QStringLiteral(
        "规则：\\n"
        "1) 只输出译文，不要解释、不要加引号、不要输出原文；\\n"
        "2) 保留段落、换行、列表编号与缩进；\\n"
        "3) 代码、URL、邮箱、数字、专有名词原样保留；\\n"
        "4) 如果原文已经是目标语言，原样返回。");""")

s = s.replace("""TranslateResult TranslateClient::translateLong(const QString& text, const QString& targetLang,
                                               const ProviderPreset& p, const QString& apiKey,
                                               const QString& glossary, int chunkChars,
                                               bool useCache) {""",
"""TranslateResult TranslateClient::translateLong(const QString& text, const QString& targetLang,
                                               const ProviderPreset& p, const QString& apiKey,
                                               const QString& glossary, int chunkChars,
                                               bool useCache, const QString& sourceLang) {""")
s = s.replace("""            h.addData("|" + p.model.toUtf8() + "|" + targetLang.toUtf8() + "|" + glossary.toUtf8());""",
"""            h.addData("|" + p.model.toUtf8() + "|" + targetLang.toUtf8() + "|" + glossary.toUtf8()
                      + "|" + sourceLang.toUtf8());""")
s = s.replace("        TranslateResult r = doRequest(c, targetLang, p, apiKey, 45000, true, glossary);",
              "        TranslateResult r = doRequest(c, targetLang, p, apiKey, 45000, true, glossary, sourceLang);")

s = s.replace("""TranslateResult TranslateClient::translateLine(const QString& text, const QString& targetLang,
                                               const ProviderPreset& p, const QString& apiKey,
                                               const QString& glossary) {""",
"""TranslateResult TranslateClient::translateLine(const QString& text, const QString& targetLang,
                                               const ProviderPreset& p, const QString& apiKey,
                                               const QString& glossary, const QString& sourceLang) {""")
s = s.replace("    return doRequest(text, targetLang, p, apiKey, 30000, false, glossary);",
              "    return doRequest(text, targetLang, p, apiKey, 30000, false, glossary, sourceLang);")

s = s.replace("""TranslateResult TranslateClient::doRequest(const QString& text, const QString& targetLang,
                                             const ProviderPreset& p, const QString& apiKey,
                                             int timeoutMs, bool allowRetry, const QString& glossary) {""",
"""TranslateResult TranslateClient::doRequest(const QString& text, const QString& targetLang,
                                             const ProviderPreset& p, const QString& apiKey,
                                             int timeoutMs, bool allowRetry, const QString& glossary,
                                             const QString& sourceLang) {""")
s = s.replace('    sys["content"] = buildPrompt(targetLang, glossary);',
              '    sys["content"] = buildPrompt(targetLang, glossary, sourceLang);')
io.open(p, "w", encoding="utf-8").write(s)
print("translate source-language support added")
