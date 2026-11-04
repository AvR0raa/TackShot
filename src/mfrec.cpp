#include "mfrec.h"
#include <QDir>

#ifdef Q_OS_WIN
#include <windows.h>
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <mferror.h>
#include <QDebug>
#endif

#ifdef Q_OS_WIN

namespace {

inline qint64 pack2(UINT32 a, UINT32 b) { return (qint64(a) << 32) | b; }

// RGB32(BGRA) -> NV12 (BT.601)
void convertNv12(const QImage& img, BYTE* dst, int w, int h, int dstStride) {
    QImage s = img.convertToFormat(QImage::Format_RGB32);
    for (int y = 0; y < h; ++y) {
        const QRgb* line = reinterpret_cast<const QRgb*>(s.constScanLine(y));
        BYTE* p = dst + size_t(y) * dstStride;
        for (int x = 0; x < w; ++x) {
            int r = qRed(line[x]), g = qGreen(line[x]), b = qBlue(line[x]);
            int Y = int(0.257 * r + 0.504 * g + 0.098 * b) + 16;
            p[x] = BYTE(qBound(0, Y, 255));
        }
    }
    BYTE* uv = dst + size_t(dstStride) * h;
    for (int y = 0; y < h / 2; ++y) {
        BYTE* p = uv + size_t(y) * dstStride;
        for (int x = 0; x < w / 2; ++x) {
            int r = 0, g = 0, b = 0;
            for (int dy = 0; dy < 2; ++dy)
                for (int dx = 0; dx < 2; ++dx) {
                    QRgb c = reinterpret_cast<const QRgb*>(s.constScanLine(y * 2 + dy))[x * 2 + dx];
                    r += qRed(c); g += qGreen(c); b += qBlue(c);
                }
            r /= 4; g /= 4; b /= 4;
            int U = int(-0.148 * r - 0.291 * g + 0.439 * b) + 128;
            int V = int(0.439 * r - 0.368 * g - 0.071 * b) + 128;
            p[x * 2] = BYTE(qBound(0, U, 255));
            p[x * 2 + 1] = BYTE(qBound(0, V, 255));
        }
    }
}

} // namespace

Mp4Recorder::Mp4Recorder() {}
Mp4Recorder::~Mp4Recorder() { shutdown(); }

bool Mp4Recorder::initMf() {
    if (m_mfUp) return true;
    HRESULT hr = MFStartup(MF_VERSION, MFSTARTUP_NOSOCKET);
    if (FAILED(hr)) {
        m_error = QStringLiteral("MFStartup 失败 0x%1").arg(quint32(hr), 0, 16);
        return false;
    }
    m_mfUp = true;
    return true;
}

bool Mp4Recorder::open(const QString& path, int width, int height, int fps, int bitrateKbps,
                       bool withAudio, int audioRate, int audioChannels) {
    if (!initMf()) return false;
    m_w = width & ~1; m_h = height & ~1; m_fps = fps; m_frames = 0; m_pts = 0;
    m_hasAudio = withAudio; m_audioRate = audioRate; m_audioCh = audioChannels; m_audioPts = 0;

    QString unixPath = QDir::toNativeSeparators(path);
    IMFSinkWriter* writer = nullptr;
    HRESULT hr = MFCreateSinkWriterFromURL(
        reinterpret_cast<LPCWSTR>(unixPath.utf16()), nullptr, nullptr, &writer);
    if (FAILED(hr)) {
        m_error = QStringLiteral("创建 SinkWriter 失败 0x%1").arg(quint32(hr), 0, 16);
        return false;
    }

    IMFMediaType* outType = nullptr;
    MFCreateMediaType(&outType);
    outType->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Video);
    outType->SetGUID(MF_MT_SUBTYPE, MFVideoFormat_H264);
    outType->SetUINT32(MF_MT_AVG_BITRATE, UINT32(bitrateKbps) * 1000);
    outType->SetUINT32(MF_MT_INTERLACE_MODE, MFVideoInterlace_Progressive);
    outType->SetUINT32(MF_MT_MPEG2_PROFILE, 77);   // eAVEncH264VProfile_Main
    MFSetAttributeSize(outType, MF_MT_FRAME_SIZE, m_w, m_h);
    MFSetAttributeRatio(outType, MF_MT_FRAME_RATE, m_fps, 1);
    MFSetAttributeRatio(outType, MF_MT_PIXEL_ASPECT_RATIO, 1, 1);

    hr = writer->AddStream(outType, &m_streamIndex);
    outType->Release();
    if (FAILED(hr)) {
        m_error = QStringLiteral("AddStream 失败 0x%1").arg(quint32(hr), 0, 16);
        writer->Release();
        return false;
    }

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
    }

    // 先试 RGB32，失败再退 NV12
    auto makeInput = [&](const GUID& sub) -> IMFMediaType* {
        IMFMediaType* t = nullptr;
        MFCreateMediaType(&t);
        t->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Video);
        t->SetGUID(MF_MT_SUBTYPE, sub);
        t->SetUINT32(MF_MT_INTERLACE_MODE, MFVideoInterlace_Progressive);
        MFSetAttributeSize(t, MF_MT_FRAME_SIZE, m_w, m_h);
        MFSetAttributeRatio(t, MF_MT_FRAME_RATE, m_fps, 1);
        MFSetAttributeRatio(t, MF_MT_PIXEL_ASPECT_RATIO, 1, 1);
        return t;
    };

    IMFMediaType* inType = makeInput(MFVideoFormat_RGB32);
    hr = writer->SetInputMediaType(m_streamIndex, inType, nullptr);
    inType->Release();
    m_inputNv12 = false;
    if (FAILED(hr)) {
        IMFMediaType* nv = makeInput(MFVideoFormat_NV12);
        hr = writer->SetInputMediaType(m_streamIndex, nv, nullptr);
        nv->Release();
        m_inputNv12 = true;
    }
    if (FAILED(hr)) {
        m_error = QStringLiteral("设置输入格式失败 0x%1").arg(quint32(hr), 0, 16);
        writer->Release();
        return false;
    }

    hr = writer->BeginWriting();
    if (FAILED(hr)) {
        m_error = QStringLiteral("BeginWriting 失败 0x%1").arg(quint32(hr), 0, 16);
        writer->Release();
        return false;
    }
    m_writer = writer;
    m_started = true;
    m_clock.start();
    return true;
}

bool Mp4Recorder::writeFrame(const QImage& img) {
    if (!m_started || !m_writer) return false;
    IMFSinkWriter* writer = static_cast<IMFSinkWriter*>(m_writer);
    QImage src = img;
    if (src.width() != m_w || src.height() != m_h)
        src = src.scaled(m_w, m_h, Qt::IgnoreAspectRatio, Qt::SmoothTransformation);

    const int stride = m_inputNv12 ? m_w : m_w * 4;
    const int bytes = m_inputNv12 ? stride * m_h * 3 / 2 : stride * m_h;

    IMFMediaBuffer* buf = nullptr;
    if (FAILED(MFCreateMemoryBuffer(bytes, &buf))) return false;
    BYTE* dst = nullptr;
    if (FAILED(buf->Lock(&dst, nullptr, nullptr))) { buf->Release(); return false; }

    if (m_inputNv12) {
        convertNv12(src, dst, m_w, m_h, stride);
    } else {
        QImage s = src.convertToFormat(QImage::Format_RGB32);
        // Media Foundation 的 RGB32 输入是 bottom-up（DIB 约定），逐行倒序拷贝
        for (int y = 0; y < m_h; ++y)
            memcpy(dst + size_t(m_h - 1 - y) * stride, s.constScanLine(y), size_t(m_w) * 4);
    }
    buf->Unlock();
    buf->SetCurrentLength(bytes);

    IMFSample* sample = nullptr;
    MFCreateSample(&sample);
    sample->AddBuffer(buf);
    buf->Release();

    const LONGLONG dur = 10'000'000LL / m_fps;
    // 用真实时间做时间戳：编码跟不上时会丢帧而不是整体加速
    LONGLONG now = LONGLONG(m_clock.nsecsElapsed() / 100);
    if (now <= m_pts) now = m_pts + dur;
    sample->SetSampleTime(now);
    sample->SetSampleDuration(dur);
    m_pts = now;

    HRESULT hr = writer->WriteSample(m_streamIndex, sample);
    sample->Release();
    if (FAILED(hr)) {
        m_error = QStringLiteral("WriteSample 失败 0x%1").arg(quint32(hr), 0, 16);
        return false;
    }
    m_frames++;
    return true;
}

bool Mp4Recorder::writeAudio(const QByteArray& pcm16) {
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

bool Mp4Recorder::close() {
    if (m_writer) {
        IMFSinkWriter* writer = static_cast<IMFSinkWriter*>(m_writer);
        writer->Finalize();
        writer->Release();
        m_writer = nullptr;
    }
    m_started = false;
    shutdown();
    return m_frames > 0;
}

void Mp4Recorder::shutdown() {
    if (m_mfUp) { MFShutdown(); m_mfUp = false; }
}

#else
Mp4Recorder::Mp4Recorder() {}
Mp4Recorder::~Mp4Recorder() {}
bool Mp4Recorder::open(const QString&, int, int, int, int) { return false; }
bool Mp4Recorder::writeFrame(const QImage&) { return false; }
bool Mp4Recorder::writeAudio(const QByteArray& pcm16) {
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

bool Mp4Recorder::close() { return false; }
#endif
