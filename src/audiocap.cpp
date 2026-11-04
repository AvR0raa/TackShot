#include "audiocap.h"

#ifdef Q_OS_WIN
#include <windows.h>
#include <mmdeviceapi.h>
#include <audioclient.h>
#include <ksmedia.h>
#include <QDebug>
#include <cmath>

namespace {
const CLSID CLSID_MMDeviceEnumerator_ = __uuidof(MMDeviceEnumerator);
const IID IID_IMMDeviceEnumerator_ = __uuidof(IMMDeviceEnumerator);
const IID IID_IAudioClient_ = __uuidof(IAudioClient);
const IID IID_IAudioCaptureClient_ = __uuidof(IAudioCaptureClient);

bool ensureCom() {
    HRESULT hr = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    return SUCCEEDED(hr) || hr == RPC_E_CHANGED_MODE || hr == S_FALSE;
}

// KSDATAFORMAT_SUBTYPE_IEEE_FLOAT = {00000003-0000-0010-8000-00AA00389B71}
static const GUID kFloatSubtype =
    {0x00000003, 0x0000, 0x0010, {0x80, 0x00, 0x00, 0xaa, 0x00, 0x38, 0x9b, 0x71}};

bool isFloatFormat(const WAVEFORMATEX* f) {
    if (f->wFormatTag == WAVE_FORMAT_IEEE_FLOAT) return true;
    if (f->wFormatTag == WAVE_FORMAT_EXTENSIBLE) {
        const auto* e = reinterpret_cast<const WAVEFORMATEXTENSIBLE*>(f);
        return IsEqualGUID(e->SubFormat, kFloatSubtype) != 0;
    }
    return false;
}
}

AudioCapture::AudioCapture() {}
AudioCapture::~AudioCapture() { stop(); }

bool AudioCapture::start(Source src) {
    if (!ensureCom()) { m_error = QStringLiteral("COM 初始化失败"); return false; }

    IMMDeviceEnumerator* enumerator = nullptr;
    HRESULT hr = CoCreateInstance(CLSID_MMDeviceEnumerator_, nullptr, CLSCTX_ALL,
                                  IID_IMMDeviceEnumerator_, (void**)&enumerator);
    if (FAILED(hr) || !enumerator) {
        m_error = QStringLiteral("无法创建音频设备枚举器 0x%1").arg(quint32(hr), 0, 16);
        return false;
    }

    IMMDevice* device = nullptr;
    hr = enumerator->GetDefaultAudioEndpoint(src == SystemLoopback ? eRender : eCapture,
                                             eConsole, &device);
    enumerator->Release();
    if (FAILED(hr) || !device) {
        m_error = QStringLiteral("找不到默认音频设备 0x%1").arg(quint32(hr), 0, 16);
        return false;
    }

    IAudioClient* client = nullptr;
    hr = device->Activate(IID_IAudioClient_, CLSCTX_ALL, nullptr, (void**)&client);
    device->Release();
    if (FAILED(hr) || !client) {
        m_error = QStringLiteral("激活 IAudioClient 失败 0x%1").arg(quint32(hr), 0, 16);
        return false;
    }

    // 直接使用设备混音格式（通常是 48kHz float32 立体声），不做系统级重采样
    WAVEFORMATEX* mix = nullptr;
    hr = client->GetMixFormat(&mix);
    if (FAILED(hr) || !mix) {
        m_error = QStringLiteral("GetMixFormat 失败 0x%1").arg(quint32(hr), 0, 16);
        client->Release();
        return false;
    }
    m_rate = int(mix->nSamplesPerSec);
    m_channels = int(mix->nChannels);
    m_float = isFloatFormat(mix);

    DWORD flags = 0;   // 轮询模式即可，不注册事件回调
    if (src == SystemLoopback) flags |= AUDCLNT_STREAMFLAGS_LOOPBACK;

    const REFERENCE_TIME dur = 10000000 / 4;   // 250ms
    hr = client->Initialize(AUDCLNT_SHAREMODE_SHARED, flags, dur, 0, mix, nullptr);
    CoTaskMemFree(mix);
    if (FAILED(hr)) {
        m_error = QStringLiteral("Initialize 失败 0x%1").arg(quint32(hr), 0, 16);
        client->Release();
        return false;
    }

    IAudioCaptureClient* capture = nullptr;
    hr = client->GetService(IID_IAudioCaptureClient_, (void**)&capture);
    if (FAILED(hr) || !capture) {
        m_error = QStringLiteral("GetService 失败 0x%1").arg(quint32(hr), 0, 16);
        client->Release();
        return false;
    }

    hr = client->Start();
    if (FAILED(hr)) {
        m_error = QStringLiteral("Start 失败 0x%1").arg(quint32(hr), 0, 16);
        capture->Release();
        client->Release();
        return false;
    }

    m_client = client;
    m_capture = capture;
    m_active = true;
    return true;
}

QByteArray AudioCapture::read() {
    QByteArray out;
    if (!m_active || !m_capture) return out;
    IAudioCaptureClient* capture = static_cast<IAudioCaptureClient*>(m_capture);

    UINT32 packet = 0;
    while (SUCCEEDED(capture->GetNextPacketSize(&packet)) && packet > 0) {
        BYTE* data = nullptr;
        UINT32 frames = 0;
        DWORD flags = 0;
        if (FAILED(capture->GetBuffer(&data, &frames, &flags, nullptr, nullptr))) break;

        const int samples = int(frames) * m_channels;
        if (flags & AUDCLNT_BUFFERFLAGS_SILENT) {
            out.append(samples * 2, '\0');
        } else if (data) {
            if (m_float) {
                const float* src = reinterpret_cast<const float*>(data);
                int start = out.size();
                out.resize(start + samples * 2);
                qint16* dst = reinterpret_cast<qint16*>(out.data() + start);
                for (int i = 0; i < samples; ++i) {
                    float v = src[i];
                    if (v > 1.0f) v = 1.0f;
                    if (v < -1.0f) v = -1.0f;
                    dst[i] = qint16(std::lround(v * 32767.0f));
                }
            } else {
                // 16bit PCM 直接拷贝；其它位深按 16bit 处理（少见）
                out.append(reinterpret_cast<const char*>(data), samples * 2);
            }
        }
        capture->ReleaseBuffer(frames);
    }
    return out;
}

void AudioCapture::stop() {
    if (m_client) {
        static_cast<IAudioClient*>(m_client)->Stop();
        static_cast<IAudioClient*>(m_client)->Release();
        m_client = nullptr;
    }
    if (m_capture) {
        static_cast<IAudioCaptureClient*>(m_capture)->Release();
        m_capture = nullptr;
    }
    m_active = false;
}

#else
AudioCapture::AudioCapture() {}
AudioCapture::~AudioCapture() {}
bool AudioCapture::start(Source) { return false; }
QByteArray AudioCapture::read() { return QByteArray(); }
void AudioCapture::stop() {}
#endif
