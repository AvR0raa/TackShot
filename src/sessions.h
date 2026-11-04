#pragma once
#include <QWidget>
#include <QRect>
#include <QImage>
#include <QVector>
#include "mfrec.h"
#include "audiocap.h"

class QLabel;
class QTimer;
class QPushButton;

// 抓取屏幕上一个物理像素区域（虚拟桌面裁剪）
QImage grabRegion(const QRect& physRegion);

// 长截图：定时抓取 + 自动拼接
class LongShotBar : public QWidget {
    Q_OBJECT
public:
    explicit LongShotBar(const QRect& physRegion, QWidget* parent = nullptr);

signals:
    void finished(QImage result);
    void cancelled();

private:
    void tick();
    void doFinish();

    QRect m_region;
    QImage m_canvas;
    QImage m_prev;
    QTimer* m_timer = nullptr;
    QLabel* m_info = nullptr;
    QLabel* m_preview = nullptr;
    int m_frames = 0;
    int m_rolledBack = 0;
    int m_dir = 0;
};

// GIF 录制
class RecordBar : public QWidget {
    Q_OBJECT
public:
    explicit RecordBar(const QRect& physRegion, QWidget* parent = nullptr);
    ~RecordBar() override;

signals:
    void finished(QString path);
    void cancelled();

private:
    void tick();
    void doStop(bool save);

    QRect m_region;
    QTimer* m_timer = nullptr;
    QLabel* m_info = nullptr;
    void* m_enc = nullptr;      // GifEncoder*
    Mp4Recorder* m_mp4 = nullptr;
    AudioCapture* m_audioA = nullptr;
    AudioCapture* m_audioB = nullptr;
    bool m_useMp4 = false;
    qint64 m_startMs = 0;
    int m_frames = 0;
    int m_rolledBack = 0;
    QString m_path;
    QPoint m_dragOffset;
    bool m_dragging = false;

protected:
    void paintEvent(QPaintEvent*) override;
    void mousePressEvent(QMouseEvent*) override;
    void mouseMoveEvent(QMouseEvent*) override;
    void mouseReleaseEvent(QMouseEvent*) override;
};
