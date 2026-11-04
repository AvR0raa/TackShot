import io

# ---- config.h
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\config.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace('    bool translatePrivacyAccepted = false;',
"""    bool translatePrivacyAccepted = false;
    QString translateFallbackProvider;            // 空 = 不降级
    QString translateFallbackBaseUrl;
    QString translateFallbackModel;
    QString translateGlossary;                    // 每行 "原文=译法"
    int translateChunkChars = 1500;""")
io.open(p, "w", encoding="utf-8").write(s)

# ---- config.cpp
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\config.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace('    o["translatePrivacyAccepted"] = translatePrivacyAccepted;',
"""    o["translatePrivacyAccepted"] = translatePrivacyAccepted;
    o["translateFallbackProvider"] = translateFallbackProvider;
    o["translateFallbackBaseUrl"] = translateFallbackBaseUrl;
    o["translateFallbackModel"] = translateFallbackModel;
    o["translateGlossary"] = translateGlossary;
    o["translateChunkChars"] = translateChunkChars;""")
s = s.replace('    if (o.contains("translatePrivacyAccepted")) translatePrivacyAccepted = o["translatePrivacyAccepted"].toBool();',
"""    if (o.contains("translatePrivacyAccepted")) translatePrivacyAccepted = o["translatePrivacyAccepted"].toBool();
    if (o.contains("translateFallbackProvider")) translateFallbackProvider = o["translateFallbackProvider"].toString();
    if (o.contains("translateFallbackBaseUrl")) translateFallbackBaseUrl = o["translateFallbackBaseUrl"].toString();
    if (o.contains("translateFallbackModel")) translateFallbackModel = o["translateFallbackModel"].toString();
    if (o.contains("translateGlossary")) translateGlossary = o["translateGlossary"].toString();
    if (o.contains("translateChunkChars")) translateChunkChars = int(o["translateChunkChars"].toDouble());""")
io.open(p, "w", encoding="utf-8").write(s)

# ---- settingsdialog.h
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    QLabel*           m_trStatus = nullptr;",
"""    QLabel*           m_trStatus = nullptr;
    QComboBox*        m_trFallback = nullptr;
    QLineEdit*        m_trFallbackKey = nullptr;
    QPlainTextEdit*   m_trGlossary = nullptr;
    QSpinBox*         m_trChunk = nullptr;""")
s = s.replace("class QLabel;", "class QLabel;\nclass QPlainTextEdit;\nclass QSpinBox;")
io.open(p, "w", encoding="utf-8").write(s)
print("config + settings header ok")
