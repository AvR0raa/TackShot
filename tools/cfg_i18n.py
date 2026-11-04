import io

# ---------------- config.h ----------------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\config.h"
s = io.open(p, encoding="utf-8").read()
if "translateSource" not in s:
    s = s.replace('    QString translateTarget = "简体中文";',
'''    QString translateSource = "English";       // 源语言（默认英文，可设“自动检测”）
    QString translateTarget = "简体中文";        // 目标语言''')
if "ocrBackend" not in s:
    s = s.replace('    bool copyAfterCapture = true;',
'''    // 识别（OCR）
    QString ocrBackend = "local";               // local / online / auto
    bool    ocrFormula = true;                  // 是否启用公式识别
    bool    ocrPrivacyAccepted = false;         // 在线识别隐私确认
    QString visionProvider = "gemini";          // 视觉模型 engine（复用 translate 预设体系）
    QString visionBaseUrl;                      // 空 = 用预设
    QString visionModel;                        // 空 = 用预设

    bool copyAfterCapture = true;''')
io.open(p, "w", encoding="utf-8").write(s)

# ---------------- config.cpp ----------------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\config.cpp"
s = io.open(p, encoding="utf-8").read()
if "translateSource" not in s:
    s = s.replace('    o["translateTarget"] = translateTarget;',
                  '    o["translateSource"] = translateSource;\n    o["translateTarget"] = translateTarget;')
    s = s.replace('    if (o.contains("translateTarget")) translateTarget = o["translateTarget"].toString();',
                  '    if (o.contains("translateSource")) translateSource = o["translateSource"].toString();\n    if (o.contains("translateTarget")) translateTarget = o["translateTarget"].toString();')
if "ocrBackend" not in s:
    s = s.replace('    o["copyAfterCapture"] = copyAfterCapture;',
'''    o["ocrBackend"] = ocrBackend;
    o["ocrFormula"] = ocrFormula;
    o["ocrPrivacyAccepted"] = ocrPrivacyAccepted;
    o["visionProvider"] = visionProvider;
    o["visionBaseUrl"] = visionBaseUrl;
    o["visionModel"] = visionModel;
    o["copyAfterCapture"] = copyAfterCapture;''')
    s = s.replace('    if (o.contains("copyAfterCapture")) copyAfterCapture = o["copyAfterCapture"].toBool();',
'''    if (o.contains("ocrBackend")) ocrBackend = o["ocrBackend"].toString();
    if (o.contains("ocrFormula")) ocrFormula = o["ocrFormula"].toBool();
    if (o.contains("ocrPrivacyAccepted")) ocrPrivacyAccepted = o["ocrPrivacyAccepted"].toBool();
    if (o.contains("visionProvider")) visionProvider = o["visionProvider"].toString();
    if (o.contains("visionBaseUrl")) visionBaseUrl = o["visionBaseUrl"].toString();
    if (o.contains("visionModel")) visionModel = o["visionModel"].toString();
    if (o.contains("copyAfterCapture")) copyAfterCapture = o["copyAfterCapture"].toBool();''')
io.open(p, "w", encoding="utf-8").write(s)
print("config extended")
