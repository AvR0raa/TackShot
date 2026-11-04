import io

# ---------- sessions.h：录制条加绘制/拖动 ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\sessions.h"
s = io.open(p, encoding="utf-8").read()
s = s.replace("""    void tick();
    void doStop(bool save);

    QRect m_region;""",
"""    void tick();
    void doStop(bool save);

    QRect m_region;""")
s = s.replace("""    qint64 m_startMs = 0;
    int m_frames = 0;
    QString m_path;
};""",
"""    qint64 m_startMs = 0;
    int m_frames = 0;
    QString m_path;
    QPoint m_dragOffset;
    bool m_dragging = false;

protected:
    void paintEvent(QPaintEvent*) override;
    void mousePressEvent(QMouseEvent*) override;
    void mouseMoveEvent(QMouseEvent*) override;
    void mouseReleaseEvent(QMouseEvent*) override;
};""")
io.open(p, "w", encoding="utf-8").write(s)

# ---------- sessions.cpp：重写 RecordBar ----------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\sessions.cpp"
s = io.open(p, encoding="utf-8").read()
idx = s.index("RecordBar::RecordBar")
head = s[:idx]
new = r'''RecordBar::RecordBar(const QRect& physRegion, QWidget* parent)
    : QWidget(parent), m_region(physRegion) {
    setWindowFlags(Qt::FramelessWindowHint | Qt::WindowStaysOnTopHint | Qt::Tool);
    setAttribute(Qt::WA_DeleteOnClose);
    setAttribute(Qt::WA_TranslucentBackground, true);
    setFixedSize(248, 52);

    QRect scr = QGuiApplication::primaryScreen()->geometry();
    double dpr = QGuiApplication::primaryScreen()->devicePixelRatio();
    int selLeft = int(physRegion.left() / dpr);
    int selTop = int(physRegion.top() / dpr);
    int selRight = int(physRegion.right() / dpr);
    int selBottom = int(physRegion.bottom() / dpr);

    // 放在选区外侧，避免遮挡录制内容
    int x = selRight - width();
    int y = selBottom + 12;
    if (y + height() > scr.bottom()) y = selTop - height() - 12;
    if (y < scr.top()) y = scr.top() + 12;
    if (x < scr.left()) x = scr.left() + 12;
    if (x + width() > scr.right()) x = scr.right() - width() - 12;
    move(x, y);

    m_useMp4 = (Config::get().recordFormat.compare("mp4", Qt::CaseInsensitive) == 0);
    int w = m_region.width(), h = m_region.height();
    if (m_useMp4) {
        if (w > 1920) { h = int(h * 1920.0 / w); w = 1920; }
    } else {
        if (w > 1280) { h = int(h * 1280.0 / w); w = 1280; }
    }
    h &= ~1; w &= ~1;
    if (w < 16) w = 16;
    if (h < 16) h = 16;

    QString dir = Config::get().saveDir;
    QDir().mkpath(dir);
    QString stamp = QDateTime::currentDateTime().toString("yyyyMMdd_HHmmss");
    QString audioSel = Config::get().recordAudio;

    // 先起音频采集，才能知道真实的采样率/声道
    if (m_useMp4 && audioSel != "none" && !audioSel.isEmpty()) {
        if (audioSel == "system" || audioSel == "both") {
            m_audioA = new AudioCapture();
            if (!m_audioA->start(AudioCapture::SystemLoopback)) { delete m_audioA; m_audioA = nullptr; }
        }
        if (audioSel == "mic" || audioSel == "both") {
            m_audioB = new AudioCapture();
            if (!m_audioB->start(AudioCapture::Microphone)) { delete m_audioB; m_audioB = nullptr; }
        }
    }
    int aRate = 48000, aCh = 2;
    if (m_audioA) { aRate = m_audioA->sampleRate(); aCh = m_audioA->channels(); }

    QImage first = grabRegion(m_region);

    if (m_useMp4) {
        m_path = QString("%1/record_%2.mp4").arg(dir, stamp);
        bool useAudio = (m_audioA != nullptr);
        m_mp4 = new Mp4Recorder();
        if (!m_mp4->open(m_path, w, h, 15, 8000, useAudio, aRate, aCh)) {
            QMessageBox::warning(nullptr, QStringLiteral("录制"), m_mp4->lastError());
            delete m_mp4; m_mp4 = nullptr;
            if (m_audioA) { m_audioA->stop(); delete m_audioA; m_audioA = nullptr; }
            if (m_audioB) { m_audioB->stop(); delete m_audioB; m_audioB = nullptr; }
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

void RecordBar::paintEvent(QPaintEvent*) {
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing, true);
    QRectF r = rect().adjusted(1, 1, -1, -1);
    p.setPen(QPen(QColor(0, 0, 0, 60), 1));
    p.setBrush(QColor(28, 30, 34, 238));
    p.drawRoundedRect(r, 10, 10);

    // 红点
    p.setPen(Qt::NoPen);
    p.setBrush(QColor("#ff453a"));
    p.drawEllipse(QPointF(20, 18), 5, 5);

    // 时间
    qint64 ms = QDateTime::currentMSecsSinceEpoch() - m_startMs;
    QString t = QString("%1:%2").arg(ms / 60000).arg((ms / 1000) % 60, 2, 10, QChar('0'));
    p.setPen(QColor("#f2f4f7"));
    QFont f = font();
    f.setPixelSize(14);
    f.setBold(true);
    p.setFont(f);
    p.drawText(QRectF(34, 8, 90, 22), Qt::AlignLeft | Qt::AlignVCenter, t);

    f.setPixelSize(11);
    f.setBold(false);
    p.setFont(f);
    p.setPen(QColor("#9aa0a6"));
    p.drawText(QRectF(96, 8, 60, 22), Qt::AlignLeft | Qt::AlignVCenter,
               QString("%1 帧").arg(m_frames));

    // 停止按钮
    QRectF stopBtn(150, 30, 44, 18);
    p.setBrush(QColor("#ff453a"));
    p.drawRoundedRect(stopBtn, 4, 4);
    p.setPen(QColor("white"));
    f.setPixelSize(11);
    p.setFont(f);
    p.drawText(stopBtn, Qt::AlignCenter, QStringLiteral("停止"));

    QRectF cancelBtn(198, 30, 40, 18);
    p.setBrush(QColor(70, 74, 80));
    p.drawRoundedRect(cancelBtn, 4, 4);
    p.setPen(QColor("#e8eaed"));
    p.drawText(cancelBtn, Qt::AlignCenter, QStringLiteral("取消"));

    // 提示：可拖动
    p.setPen(QColor(120, 126, 134));
    p.drawText(QRectF(150, 6, 90, 18), Qt::AlignRight | Qt::AlignVCenter, QStringLiteral("可拖动"));
}

void RecordBar::mousePressEvent(QMouseEvent* e) {
    if (e->button() != Qt::LeftButton) return;
    QPointF pos = e->position();
    if (QRectF(150, 30, 44, 18).contains(pos)) { doStop(true); return; }
    if (QRectF(198, 30, 40, 18).contains(pos)) { doStop(false); return; }
    m_dragging = true;
    m_dragOffset = e->globalPosition().toPoint() - frameGeometry().topLeft();
}

void RecordBar::mouseMoveEvent(QMouseEvent* e) {
    if (m_dragging) move(e->globalPosition().toPoint() - m_dragOffset);
}

void RecordBar::mouseReleaseEvent(QMouseEvent*) { m_dragging = false; }

RecordBar::~RecordBar() {
    if (m_enc) { delete static_cast<GifEncoder*>(m_enc); m_enc = nullptr; }
    if (m_mp4) { delete m_mp4; m_mp4 = nullptr; }
    if (m_audioA) { delete m_audioA; m_audioA = nullptr; }
    if (m_audioB) { delete m_audioB; m_audioB = nullptr; }
}

void RecordBar::tick() {
    QImage f = grabRegion(m_region);
    if (!f.isNull()) {
        if (m_mp4) m_mp4->writeFrame(f);
        else if (m_enc) static_cast<GifEncoder*>(m_enc)->addFrame(f);
        m_frames++;
    }

    if (m_mp4 && (m_audioA || m_audioB)) {
        QByteArray a = m_audioA ? m_audioA->read() : QByteArray();
        QByteArray b = m_audioB ? m_audioB->read() : QByteArray();
        bool canMix = m_audioA && m_audioB &&
                      m_audioA->sampleRate() == m_audioB->sampleRate() &&
                      m_audioA->channels() == m_audioB->channels();
        if (canMix) {
            int n = qMax(a.size(), b.size());
            a.resize(n); b.resize(n);
            qint16* pa = reinterpret_cast<qint16*>(a.data());
            const qint16* pb = reinterpret_cast<const qint16*>(b.constData());
            int cnt = n / 2;
            for (int i = 0; i < cnt; ++i)
                pa[i] = qint16((int(pa[i]) + int(pb[i])) / 2);   // 取平均，避免削波
        }
        if (!a.isEmpty()) m_mp4->writeAudio(a);
    }

    qint64 ms = QDateTime::currentMSecsSinceEpoch() - m_startMs;
    update();
    if (ms > 10 * 60 * 1000) doStop(true);
}

void RecordBar::doStop(bool save) {
    if (m_timer) m_timer->stop();
    if (m_audioA) { m_audioA->stop(); delete m_audioA; m_audioA = nullptr; }
    if (m_audioB) { m_audioB->stop(); delete m_audioB; m_audioB = nullptr; }
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
s = s.replace('#include <QElapsedTimer>', '#include <QElapsedTimer>\n#include <QPainter>\n#include <QMouseEvent>')
io.open(p, "w", encoding="utf-8").write(s)
print("RecordBar redesigned")
