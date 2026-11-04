import io

# sessions.h：音频成员
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\sessions.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace('#include "mfrec.h"', '#include "mfrec.h"\n#include "audiocap.h"')
s = s.replace("    Mp4Recorder* m_mp4 = nullptr;",
              "    Mp4Recorder* m_mp4 = nullptr;\n    AudioCapture* m_audioA = nullptr;\n    AudioCapture* m_audioB = nullptr;")
io.open(p, "w", encoding="utf-8").write(s)

# sessions.cpp：启动/停止/写入音频
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\sessions.cpp"
s = io.open(p, encoding="utf-8").read()

old = """    if (m_useMp4) {
        m_path = QString("%1/record_%2.mp4").arg(dir, stamp);
        m_mp4 = new Mp4Recorder();
        if (!m_mp4->open(m_path, w, h, 15, 6000)) {"""
new = """    if (m_useMp4) {
        m_path = QString("%1/record_%2.mp4").arg(dir, stamp);
        QString audioSel = Config::get().recordAudio;
        bool useAudio = (audioSel != "none" && !audioSel.isEmpty());
        m_mp4 = new Mp4Recorder();
        if (!m_mp4->open(m_path, w, h, 15, 6000, useAudio)) {"""
if old in s:
    s = s.replace(old, new, 1)

old2 = """        if (!first.isNull()) { m_mp4->writeFrame(first); m_frames++; }
        m_startMs = QDateTime::currentMSecsSinceEpoch();"""
new2 = """        if (useAudio) {
            if (audioSel == "system" || audioSel == "both") {
                m_audioA = new AudioCapture();
                if (!m_audioA->start(AudioCapture::SystemLoopback)) {
                    delete m_audioA; m_audioA = nullptr;
                }
            }
            if (audioSel == "mic" || audioSel == "both") {
                m_audioB = new AudioCapture();
                if (!m_audioB->start(AudioCapture::Microphone)) {
                    delete m_audioB; m_audioB = nullptr;
                }
            }
        }
        if (!first.isNull()) { m_mp4->writeFrame(first); m_frames++; }
        m_startMs = QDateTime::currentMSecsSinceEpoch();"""
if old2 in s:
    s = s.replace(old2, new2, 1)

old3 = """void RecordBar::tick() {
    QImage f = grabRegion(m_region);
    if (f.isNull()) return;
    if (m_mp4) m_mp4->writeFrame(f);
    else if (m_enc) static_cast<GifEncoder*>(m_enc)->addFrame(f);
    m_frames++;"""
new3 = """void RecordBar::tick() {
    QImage f = grabRegion(m_region);
    if (!f.isNull()) {
        if (m_mp4) m_mp4->writeFrame(f);
        else if (m_enc) static_cast<GifEncoder*>(m_enc)->addFrame(f);
        m_frames++;
    }

    // 音频：每 tick 把两路数据混一起送进封装器
    if (m_mp4 && (m_audioA || m_audioB)) {
        QByteArray a = m_audioA ? m_audioA->read() : QByteArray();
        QByteArray b = m_audioB ? m_audioB->read() : QByteArray();
        if (a.size() != b.size()) {
            int n = qMax(a.size(), b.size());
            a.resize(n); b.resize(n);          // 用 0 补齐，等长叠加
        }
        if (!a.isEmpty()) {
            if (!b.isEmpty()) {
                qint16* pa = reinterpret_cast<qint16*>(a.data());
                const qint16* pb = reinterpret_cast<const qint16*>(b.constData());
                int n = a.size() / 2;
                for (int i = 0; i < n; ++i) {
                    int v = int(pa[i]) + int(pb[i]);
                    pa[i] = qint16(qBound(-32768, v, 32767));
                }
            }
            m_mp4->writeAudio(a);
        }
    }"""
if old3 in s:
    s = s.replace(old3, new3, 1)

old4 = """void RecordBar::doStop(bool save) {
    if (m_timer) m_timer->stop();"""
new4 = """void RecordBar::doStop(bool save) {
    if (m_timer) m_timer->stop();
    if (m_audioA) { m_audioA->stop(); delete m_audioA; m_audioA = nullptr; }
    if (m_audioB) { m_audioB->stop(); delete m_audioB; m_audioB = nullptr; }"""
if old4 in s:
    s = s.replace(old4, new4, 1)

s = s.replace("""    if (m_enc) { delete static_cast<GifEncoder*>(m_enc); m_enc = nullptr; }
    if (m_mp4) { delete m_mp4; m_mp4 = nullptr; }""",
"""    if (m_enc) { delete static_cast<GifEncoder*>(m_enc); m_enc = nullptr; }
    if (m_mp4) { delete m_mp4; m_mp4 = nullptr; }
    if (m_audioA) { delete m_audioA; m_audioA = nullptr; }
    if (m_audioB) { delete m_audioB; m_audioB = nullptr; }""")
io.open(p, "w", encoding="utf-8").write(s)
print("sessions audio wired")

# settingsdialog：录音源
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    QComboBox*        m_recFmt = nullptr;", "    QComboBox*        m_recFmt = nullptr;\n    QComboBox*        m_recAudio = nullptr;")
io.open(p, "w", encoding="utf-8").write(s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\settingsdialog.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace('    form->addRow(QStringLiteral("录屏格式"), m_recFmt);',
              '    form->addRow(QStringLiteral("录屏格式"), m_recFmt);\n\n'
              '    m_recAudio = new QComboBox(this);\n'
              '    m_recAudio->addItems({"none", "system", "mic", "both"});\n'
              '    m_recAudio->setCurrentText(Config::get().recordAudio);\n'
              '    form->addRow(QStringLiteral("录制音频"), m_recAudio);')
s = s.replace('    c.recordFormat = m_recFmt->currentText();',
              '    c.recordFormat = m_recFmt->currentText();\n    c.recordAudio = m_recAudio->currentText();')
io.open(p, "w", encoding="utf-8").write(s)
print("settings ok")
