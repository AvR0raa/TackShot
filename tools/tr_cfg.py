import io

# config.h
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\config.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace('    QString recordAudio = "system"; // none / system / mic / both',
              '    QString recordAudio = "system"; // none / system / mic / both\n\n'
              '    // 翻译\n'
              '    QString translateProvider = "deepseek";   // deepseek / gemini / custom\n'
              '    QString translateBaseUrl;                  // 空 = 用预设\n'
              '    QString translateModel;                    // 空 = 用预设\n'
              '    QString translateTarget = "简体中文";\n'
              '    bool translatePrivacyAccepted = false;')
io.open(p, "w", encoding="utf-8").write(s)

# config.cpp
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\config.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace('    o["recordAudio"] = recordAudio;',
              '    o["recordAudio"] = recordAudio;\n'
              '    o["translateProvider"] = translateProvider;\n'
              '    o["translateBaseUrl"] = translateBaseUrl;\n'
              '    o["translateModel"] = translateModel;\n'
              '    o["translateTarget"] = translateTarget;\n'
              '    o["translatePrivacyAccepted"] = translatePrivacyAccepted;')
s = s.replace('    if (o.contains("recordAudio")) recordAudio = o["recordAudio"].toString();',
              '    if (o.contains("recordAudio")) recordAudio = o["recordAudio"].toString();\n'
              '    if (o.contains("translateProvider")) translateProvider = o["translateProvider"].toString();\n'
              '    if (o.contains("translateBaseUrl")) translateBaseUrl = o["translateBaseUrl"].toString();\n'
              '    if (o.contains("translateModel")) translateModel = o["translateModel"].toString();\n'
              '    if (o.contains("translateTarget")) translateTarget = o["translateTarget"].toString();\n'
              '    if (o.contains("translatePrivacyAccepted")) translatePrivacyAccepted = o["translatePrivacyAccepted"].toBool();')
io.open(p, "w", encoding="utf-8").write(s)

# settingsdialog.h
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    QComboBox*        m_recAudio = nullptr;",
              "    QComboBox*        m_recAudio = nullptr;\n"
              "    QComboBox*        m_trProvider = nullptr;\n"
              "    QLineEdit*        m_trBase = nullptr;\n"
              "    QLineEdit*        m_trModel = nullptr;\n"
              "    QLineEdit*        m_trKey = nullptr;\n"
              "    QComboBox*        m_trTarget = nullptr;\n"
              "    QLabel*           m_trStatus = nullptr;")
s = s.replace("#include <QDialog>", "#include <QDialog>\nclass QLabel;")
io.open(p, "w", encoding="utf-8").write(s)
print("config+header ok")
