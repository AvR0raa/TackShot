import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.cpp"
s = io.open(p, encoding="utf-8").read()
if '#include "vision.h"' not in s:
    s = s.replace('#include "theme.h"', '#include "theme.h"\n#include "vision.h"')

old = """    probeBtn->setObjectName(QStringLiteral("tsProbeVision"));"""
new = """    probeBtn->setObjectName(QStringLiteral("tsProbeVision"));
    connect(probeBtn, &QPushButton::clicked, this, [this]() {
        m_visionStatus->setText(QStringLiteral("测试中…"));
        QApplication::processEvents();
        ProviderPreset vp = TranslateClient::presetById(m_visionProvider->currentData().toString());
        const QString base = m_visionBase->text().trimmed().isEmpty() ? vp.baseUrl : m_visionBase->text().trimmed();
        const QString model = m_visionModel->text().trimmed().isEmpty() ? vp.model : m_visionModel->text().trimmed();
        QString key = m_visionKey->text().trimmed();
        if (key.isEmpty()) key = secrets::load("vision_api_key_" + m_visionProvider->currentData().toString());
        if (key.isEmpty()) { m_visionStatus->setText(QStringLiteral("请先填写 API Key")); return; }
        VisionClient vc;
        auto r = vc.probe(base, model, key);
        m_visionStatus->setText(r.ok ? QStringLiteral("图片能力正常：%1").arg(r.text.left(30))
                                     : QStringLiteral("失败：%1").arg(r.error));
    });"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("probe wired")
else:
    print("MISS")
