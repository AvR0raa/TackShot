import io

# config.h
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\config.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace('    QString format = "png";     // png / jpg / webp',
              '    QString format = "png";     // png / jpg / webp\n    QString recordFormat = "mp4";   // mp4 / gif')
io.open(p, "w", encoding="utf-8").write(s)

# config.cpp
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\config.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace('    o["format"] = format;', '    o["format"] = format;\n    o["recordFormat"] = recordFormat;')
s = s.replace('    if (o.contains("format"))     format     = o["format"].toString();',
              '    if (o.contains("format"))     format     = o["format"].toString();\n    if (o.contains("recordFormat")) recordFormat = o["recordFormat"].toString();')
io.open(p, "w", encoding="utf-8").write(s)

# settingsdialog.h
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    QComboBox*        m_fmt = nullptr;",
              "    QComboBox*        m_fmt = nullptr;\n    QComboBox*        m_recFmt = nullptr;")
io.open(p, "w", encoding="utf-8").write(s)

# settingsdialog.cpp
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace('    form->addRow(QStringLiteral("图片格式"), m_fmt);',
              '    form->addRow(QStringLiteral("图片格式"), m_fmt);\n\n'
              '    m_recFmt = new QComboBox(this);\n'
              '    m_recFmt->addItems({"mp4", "gif"});\n'
              '    m_recFmt->setCurrentText(Config::get().recordFormat);\n'
              '    form->addRow(QStringLiteral("录屏格式"), m_recFmt);')
s = s.replace('    c.format = m_fmt->currentText();',
              '    c.format = m_fmt->currentText();\n    c.recordFormat = m_recFmt->currentText();')
io.open(p, "w", encoding="utf-8").write(s)
print("config + settings ok")
