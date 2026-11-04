import io

# ---- mfrec.h ----
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\mfrec.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    bool open(const QString& path, int width, int height, int fps, int bitrateKbps = 6000);",
              "    bool open(const QString& path, int width, int height, int fps, int bitrateKbps = 6000,\n"
              "              bool withAudio = false, int audioRate = 48000, int audioChannels = 2);\n"
              "    bool writeAudio(const QByteArray& pcm16);")
s = s.replace('#include <QElapsedTimer>', '#include <QElapsedTimer>\n#include <QByteArray>')
s = s.replace("    unsigned long m_streamIndex = 0;",
              "    unsigned long m_streamIndex = 0;\n    unsigned long m_audioIndex = 0;\n    bool m_hasAudio = false;\n    qint64 m_audioPts = 0;\n    int m_audioRate = 48000, m_audioCh = 2;")
io.open(p, "w", encoding="utf-8").write(s)

# ---- mfrec.cpp ----
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\mfrec.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("bool Mp4Recorder::open(const QString& path, int width, int height, int fps, int bitrateKbps) {",
              "bool Mp4Recorder::open(const QString& path, int width, int height, int fps, int bitrateKbps,\n"
              "                       bool withAudio, int audioRate, int audioChannels) {")
s = s.replace("    m_w = width & ~1; m_h = height & ~1; m_fps = fps; m_frames = 0; m_pts = 0;",
              "    m_w = width & ~1; m_h = height & ~1; m_fps = fps; m_frames = 0; m_pts = 0;\n"
              "    m_hasAudio = withAudio; m_audioRate = audioRate; m_audioCh = audioChannels; m_audioPts = 0;")

# 在 video AddStream 之后插入音频流
anchor = """    hr = writer->AddStream(outType, &m_streamIndex);
    outType->Release();
    if (FAILED(hr)) {
        m_error = QStringLiteral("AddStream 失败 0x%1").arg(quint32(hr), 0, 16);
        writer->Release();
        return false;
    }"""
add = anchor + """

    if (withAudio) {
        IMFMediaType* aout = nullptr;
        MFCreateMediaType(&aout);
        aout->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Audio);
        aout->SetGUID(MF_MT_SUBTYPE, MFAudioFormat_AAC);
        aout->SetUINT32(MF_MT_AUDIO_BITS_PER_SAMPLE, 16);
        aout->SetUINT32(MF_MT_AUDIO_SAMPLES_PER_SECOND, UINT32(audioRate));
        aout->SetUINT32(MF_MT_AUDIO_NUM_CHANNELS, UINT32(audioChannels));
        aout->SetUINT32(MF_MT_AUDIO_AVG_BYTES_PER_SECOND, 16000);   // 128 kbps
        aout->SetUINT32(MF_MT_AAC_PAYLOAD_TYPE, 0);
        aout->SetUINT32(MF_MT_AAC_AUDIO_PROFILE_LEVEL_INDICATION, 0x29);
        hr = writer->AddStream(aout, &m_audioIndex);
        aout->Release();
        if (FAILED(hr)) {
            m_error = QStringLiteral("AddStream(audio) 失败 0x%1").arg(quint32(hr), 0, 16);
            writer->Release();
            return false;
        }

        IMFMediaType* ain = nullptr;
        MFCreateMediaType(&ain);
        ain->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Audio);
        ain->SetGUID(MF_MT_SUBTYPE, MFAudioFormat_PCM);
        ain->SetUINT32(MF_MT_AUDIO_BITS_PER_SAMPLE, 16);
        ain->SetUINT32(MF_MT_AUDIO_SAMPLES_PER_SECOND, UINT32(audioRate));
        ain->SetUINT32(MF_MT_AUDIO_NUM_CHANNELS, UINT32(audioChannels));
        ain->SetUINT32(MF_MT_AUDIO_BLOCK_ALIGNMENT, UINT32(audioChannels * 2));
        ain->SetUINT32(MF_MT_AUDIO_AVG_BYTES_PER_SECOND, UINT32(audioRate * audioChannels * 2));
        ain->SetUINT32(MF_MT_ALL_SAMPLES_INDEPENDENT, TRUE);
        hr = writer->SetInputMediaType(m_audioIndex, ain, nullptr);
        ain->Release();
        if (FAILED(hr)) {
            m_error = QStringLiteral("音频输入格式失败 0x%1").arg(quint32(hr), 0, 16);
            writer->Release();
            return false;
        }
    }"""
if anchor in s:
    s = s.replace(anchor, add, 1)

# writeAudio 实现
s = s.replace("bool Mp4Recorder::close() {", """bool Mp4Recorder::writeAudio(const QByteArray& pcm16) {
    if (!m_started || !m_writer || !m_hasAudio || pcm16.isEmpty()) return false;
    IMFSinkWriter* writer = static_cast<IMFSinkWriter*>(m_writer);

    IMFMediaBuffer* buf = nullptr;
    if (FAILED(MFCreateMemoryBuffer(UINT32(pcm16.size()), &buf))) return false;
    BYTE* dst = nullptr;
    if (FAILED(buf->Lock(&dst, nullptr, nullptr))) { buf->Release(); return false; }
    memcpy(dst, pcm16.constData(), size_t(pcm16.size()));
    buf->Unlock();
    buf->SetCurrentLength(UINT32(pcm16.size()));

    IMFSample* sample = nullptr;
    MFCreateSample(&sample);
    sample->AddBuffer(buf);
    buf->Release();

    const int bytesPerSec = m_audioRate * m_audioCh * 2;
    const LONGLONG dur = LONGLONG(pcm16.size()) * 10'000'000LL / bytesPerSec;
    sample->SetSampleTime(m_audioPts);
    sample->SetSampleDuration(dur);
    m_audioPts += dur;

    HRESULT hr = writer->WriteSample(m_audioIndex, sample);
    sample->Release();
    return SUCCEEDED(hr);
}

bool Mp4Recorder::close() {""")
io.open(p, "w", encoding="utf-8").write(s)
print("mfrec audio added")

# ---- config ----
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\config.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace('    QString recordFormat = "mp4";   // mp4 / gif',
              '    QString recordFormat = "mp4";   // mp4 / gif\n    QString recordAudio = "system"; // none / system / mic / both')
io.open(p, "w", encoding="utf-8").write(s)
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\config.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace('    o["recordFormat"] = recordFormat;', '    o["recordFormat"] = recordFormat;\n    o["recordAudio"] = recordAudio;')
s = s.replace('    if (o.contains("recordFormat")) recordFormat = o["recordFormat"].toString();',
              '    if (o.contains("recordFormat")) recordFormat = o["recordFormat"].toString();\n    if (o.contains("recordAudio")) recordAudio = o["recordAudio"].toString();')
io.open(p, "w", encoding="utf-8").write(s)
print("config ok")
