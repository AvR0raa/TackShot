import io

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace('#include <QApplication>', '#include <QApplication>\n#include <QPlainTextEdit>\n#include <QSpinBox>')

anchor = '    form->addRow(QStringLiteral("目标语言"), m_trTarget);'
add = anchor + """

    m_trFallback = new QComboBox(this);
    m_trFallback->addItem(QStringLiteral("无（不降级）"), QString());
    for (const auto& p : TranslateClient::presets())
        m_trFallback->addItem(p.name, p.id);
    {
        int idx = m_trFallback->findData(Config::get().translateFallbackProvider);
        m_trFallback->setCurrentIndex(idx >= 0 ? idx : 0);
    }
    form->addRow(QStringLiteral("备用引擎"), m_trFallback);

    m_trFallbackKey = new QLineEdit(this);
    m_trFallbackKey->setEchoMode(QLineEdit::Password);
    m_trFallbackKey->setPlaceholderText(QStringLiteral("备用引擎的 Key（可留空）"));
    {
        QString fid = Config::get().translateFallbackProvider;
        if (!fid.isEmpty()) m_trFallbackKey->setText(secrets::load("translate_api_key_" + fid));
    }
    form->addRow(QStringLiteral("备用 Key"), m_trFallbackKey);

    m_trGlossary = new QPlainTextEdit(this);
    m_trGlossary->setPlaceholderText(QStringLiteral("术语表，每行一条：原文=译法\n例如：TackShot=TackShot\n钉图=Pin Image"));
    m_trGlossary->setPlainText(Config::get().translateGlossary);
    m_trGlossary->setMaximumHeight(90);
    form->addRow(QStringLiteral("术语表"), m_trGlossary);

    m_trChunk = new QSpinBox(this);
    m_trChunk->setRange(300, 8000);
    m_trChunk->setSingleStep(100);
    m_trChunk->setValue(Config::get().translateChunkChars);
    form->addRow(QStringLiteral("分段长度(字)"), m_trChunk);"""
if anchor in s:
    s = s.replace(anchor, add, 1)

# accept(): 保存备用 key + 术语表 + 分段
s = s.replace("""    {
        QString key = m_trKey->text().trimmed();
        if (!key.isEmpty()) secrets::save("translate_api_key", key);
        else secrets::remove("translate_api_key");
    }""",
"""    {
        QString key = m_trKey->text().trimmed();
        if (!key.isEmpty()) secrets::save("translate_api_key_" + c.translateProvider, key);
        else secrets::remove("translate_api_key_" + c.translateProvider);
    }
    c.translateFallbackProvider = m_trFallback->currentData().toString();
    c.translateGlossary = m_trGlossary->toPlainText();
    c.translateChunkChars = m_trChunk->value();
    if (!c.translateFallbackProvider.isEmpty()) {
        QString fk = m_trFallbackKey->text().trimmed();
        if (!fk.isEmpty()) secrets::save("translate_api_key_" + c.translateFallbackProvider, fk);
    }""")

# 主 Key 读取：优先按 provider 存的名字，兼容旧键
s = s.replace('    QString saved = secrets::load("translate_api_key");\n    if (!saved.isEmpty()) m_trKey->setText(saved);',
"""    {
        QString cur = m_trProvider->currentData().toString();
        QString saved = secrets::load("translate_api_key_" + cur);
        if (saved.isEmpty()) saved = secrets::load("translate_api_key");
        if (!saved.isEmpty()) m_trKey->setText(saved);
    }""")
io.open(p, "w", encoding="utf-8").write(s)
print("settings fallback/glossary added")
