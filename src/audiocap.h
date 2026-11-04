#pragma once
#include <QByteArray>
#include <QString>

// WASAPI 采集：系统回环（loopback）或麦克风
// 直接使用设备混音格式采集，再在本地转成 int16，避免 Windows 低质量重采样
class AudioCapture {
public:
    enum Source { SystemLoopback = 0, Microphone = 1 };

    AudioCapture();
    ~AudioCapture();

    bool start(Source src);
    QByteArray read();          // int16 交错
    void stop();
    bool active() const { return m_active; }
    QString lastError() const { return m_error; }
    int sampleRate() const { return m_rate; }
    int channels() const { return m_channels; }

private:
    void* m_client = nullptr;   // IAudioClient*
    void* m_capture = nullptr;  // IAudioCaptureClient*
    bool m_active = false;
    bool m_float = false;
    int m_rate = 48000;
    int m_channels = 2;
    QString m_error;
};
