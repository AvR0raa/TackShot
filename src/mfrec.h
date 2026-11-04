#pragma once
#include <QImage>
#include <QString>
#include <QElapsedTimer>
#include <QByteArray>

// 基于 Windows Media Foundation 的 MP4(H.264) 录制器，无需外部 ffmpeg
class Mp4Recorder {
public:
    Mp4Recorder();
    ~Mp4Recorder();

    bool open(const QString& path, int width, int height, int fps, int bitrateKbps = 6000,
              bool withAudio = false, int audioRate = 48000, int audioChannels = 2);
    bool writeAudio(const QByteArray& pcm16);
    bool writeFrame(const QImage& img);
    bool close();

    QString lastError() const { return m_error; }
    int frameCount() const { return m_frames; }

private:
    bool initMf();
    void shutdown();
    void* m_writer = nullptr;      // IMFSinkWriter*
    void* m_stream = nullptr;      // IMFSinkWriter? (未用)
    unsigned long m_streamIndex = 0;
    unsigned long m_audioIndex = 0;
    bool m_hasAudio = false;
    qint64 m_audioPts = 0;
    int m_audioRate = 48000, m_audioCh = 2;
    int m_w = 0, m_h = 0, m_fps = 0;
    int m_frames = 0;
    qint64 m_pts = 0;              // 100ns
    QElapsedTimer m_clock;
    bool m_started = false;
    bool m_mfUp = false;
    bool m_inputNv12 = false;
    QString m_error;
};
