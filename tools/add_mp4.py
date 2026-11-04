import io

# 1) mfrec.h: add m_inputNv12
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\mfrec.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    bool m_mfUp = false;", "    bool m_mfUp = false;\n    bool m_inputNv12 = false;")
io.open(p, "w", encoding="utf-8").write(s)

# 2) mfrec.cpp: include QDir
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\mfrec.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace('#include "mfrec.h"', '#include "mfrec.h"\n#include <QDir>')
io.open(p, "w", encoding="utf-8").write(s)

# 3) sessions.h: support MP4
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\sessions.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace('#include <QVector>', '#include <QVector>\n#include "mfrec.h"')
s = s.replace("    void* m_enc = nullptr;      // GifEncoder*",
              "    void* m_enc = nullptr;      // GifEncoder*\n    Mp4Recorder* m_mp4 = nullptr;\n    bool m_useMp4 = false;")
io.open(p, "w", encoding="utf-8").write(s)

# 4) sessions.cpp: 替换 RecordBar 实现（从 ctor 到文件末尾）
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\sessions.cpp"
s = io.open(p, encoding="utf-8").read()
idx = s.index("RecordBar::RecordBar")
head = s[:idx]
new = '''RecordBar::RecordBar(const QRect& physRegion, QWidget* parent)
    : QWidget(parent), m_region(physRegion) {
    styleBar(this);
    setFixedSize(320, 64);

    auto* lay = new QHBoxLayout(this);
    lay->setContentsMargins(12, 8, 12, 8);
    m_info = new QLabel(QStringLiteral("录制中… 0.0s"), this);
    m_info->setStyleSheet("font-size:12px;");
    lay->addWidget(m_info, 1);
    auto* stop = new QPushButton(QStringLiteral("停止"), this);
    auto* cancel = new QPushButton(QStringLiteral("取消"), this);
    cancel->setObjectName("ghost");
    lay->addWidget(stop);
    lay->addWidget(cancel);

    connect(stop, &QPushButton::clicked, this, [this]() { doStop(true); });
    connect(cancel, &QPushButton::clicked, this, [this]() { doStop(false); });

    QRect scr = QGuiApplication::primaryScreen()->geometry();
    double dpr = QGuiApplication::primaryScreen()->devicePixelRatio();
    int x = int(physRegion.left() / dpr);
    int y = int(physRegion.bottom() / dpr) + 8;
    if (y + height() > scr.bottom()) y = int(physRegion.top() / dpr) - height() - 8;
    if (x + width() > scr.right()) x = scr.right() - width();
    move(qMax(0, x), qMax(0, y));

    m_useMp4 = (Config::get().recordFormat.compare("mp4", Qt::CaseInsensitive) == 0);
    int w = m_region.width(), h = m_region.height();
    if (m_useMp4) {
        if (w > 1920) { h = int(h * 1920.0 / w); w = 1920; }
    } else {
        if (w > 1280) { h = int(h * 1280.0 / w); w = 1280; }
    }
    h &= ~1; w &= ~1;               // MP4 要求偶数
    if (w < 16) w = 16;
    if (h < 16) h = 16;

    QString dir = Config::get().saveDir;
    QDir().mkpath(dir);
    QString stamp = QDateTime::currentDateTime().toString("yyyyMMdd_HHmmss");

    QImage first = grabRegion(m_region);
    if (m_useMp4) {
        m_path = QString("%1/record_%2.mp4").arg(dir, stamp);
        m_mp4 = new Mp4Recorder();
        if (!m_mp4->open(m_path, w, h, 15, 6000)) {
            QMessageBox::warning(nullptr, QStringLiteral("录制"), m_mp4->lastError());
            delete m_mp4; m_mp4 = nullptr;
            QTimer::singleShot(0, this, [this]() { emit cancelled(); close(); });
            return;
        }
        if (!first.isNull()) { m_mp4->writeFrame(first); m_frames++; }
        m_startMs = QDateTime::currentMSecsSinceEpoch();
        m_timer = new QTimer(this);
        connect(m_timer, &QTimer::timeout, this, [this]() { tick(); });
        m_timer->start(66);
        return;
    }

    m_path = QString("%1/record_%2.gif").arg(dir, stamp);
    auto* enc = new GifEncoder();
    if (!enc->open(m_path, w, h, 10)) {
        QMessageBox::warning(nullptr, QStringLiteral("录制"), QStringLiteral("无法创建 GIF 文件"));
        delete enc;
        QTimer::singleShot(0, this, [this]() { emit cancelled(); close(); });
        return;
    }
    m_enc = enc;
    if (!first.isNull()) { enc->addFrame(first); m_frames++; }
    m_startMs = QDateTime::currentMSecsSinceEpoch();
    m_timer = new QTimer(this);
    connect(m_timer, &QTimer::timeout, this, [this]() { tick(); });
    m_timer->start(100);
}

RecordBar::~RecordBar() {
    if (m_enc) { delete static_cast<GifEncoder*>(m_enc); m_enc = nullptr; }
    if (m_mp4) { delete m_mp4; m_mp4 = nullptr; }
}

void RecordBar::tick() {
    QImage f = grabRegion(m_region);
    if (f.isNull()) return;
    if (m_mp4) m_mp4->writeFrame(f);
    else if (m_enc) static_cast<GifEncoder*>(m_enc)->addFrame(f);
    m_frames++;
    double s = (QDateTime::currentMSecsSinceEpoch() - m_startMs) / 1000.0;
    m_info->setText(QStringLiteral("录制中… %1s  %2 帧").arg(s, 0, 'f', 1).arg(m_frames));
    if (s > 600) doStop(true);
}

void RecordBar::doStop(bool save) {
    if (m_timer) m_timer->stop();
    bool ok = false;
    if (m_mp4) {
        ok = m_mp4->close();
        delete m_mp4;
        m_mp4 = nullptr;
    } else if (m_enc) {
        auto* enc = static_cast<GifEncoder*>(m_enc);
        m_enc = nullptr;
        ok = enc->close();
        delete enc;
    }
    if (save && ok) {
        emit finished(m_path);
    } else {
        if (!save) QFile::remove(m_path);
        emit cancelled();
    }
    close();
}
'''
s = head + new
io.open(p, "w", encoding="utf-8").write(s)
print("sessions rewritten, len", len(s))
