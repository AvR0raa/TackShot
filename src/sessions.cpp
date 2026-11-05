#include "sessions.h"
#include "capture.h"
#include "longshot.h"
#include "gifenc.h"
#include "config.h"

#include <QTimer>
#include <QLabel>
#include <QPushButton>
#include <QHBoxLayout>
#include <QVBoxLayout>
#include <QDateTime>
#include <QDir>
#include <QApplication>
#include <QMessageBox>
#include <QScreen>
#include <QGuiApplication>
#include <QElapsedTimer>
#include <QPainter>
#include <QMouseEvent>
#include <QDebug>

QImage grabRegion(const QRect& physRegion) {
    // 小区域用 GDI 直接抓（录制每 66ms 一次，全屏回读太慢）
    QImage img = capture::captureRect(physRegion);
    if (!img.isNull()) return img;
    QRect virt;
    QImage full = capture::captureVirtualDesktop(&virt, nullptr);
    if (full.isNull()) return QImage();
    QRect r = physRegion.translated(-virt.topLeft()).intersected(QRect(0, 0, full.width(), full.height()));
    if (r.isEmpty()) return QImage();
    return full.copy(r);
}

static void styleBar(QWidget* w) {
    w->setWindowFlags(Qt::FramelessWindowHint | Qt::WindowStaysOnTopHint | Qt::Tool);
    w->setAttribute(Qt::WA_DeleteOnClose);
    w->setStyleSheet(
        "QWidget { background:#23262b; border:1px solid #3a3f47; border-radius:8px; }"
        "QLabel { color:#e8eaed; border:0; }"
        "QPushButton { background:#2f6fed; color:white; border:0; border-radius:4px; padding:5px 12px; }"
        "QPushButton#ghost { background:#3a3f47; }");
}

// ---------------- 长截图 ----------------
LongShotBar::LongShotBar(const QRect& physRegion, QWidget* parent)
    : QWidget(parent), m_region(physRegion) {
    styleBar(this);
    setFixedSize(320, 92);

    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(12, 8, 12, 8);
    m_info = new QLabel(QStringLiteral("长截图：滚动目标窗口，自动拼接"), this);
    m_info->setStyleSheet("font-size:12px;");
    lay->addWidget(m_info);

    m_preview = new QLabel(this);
    m_preview->setFixedSize(296, 28);
    m_preview->setStyleSheet("background:#1b1d21; border-radius:4px;");
    lay->addWidget(m_preview);

    auto* row = new QHBoxLayout;
    auto* done = new QPushButton(QStringLiteral("完成"), this);
    auto* cancel = new QPushButton(QStringLiteral("取消"), this);
    cancel->setObjectName("ghost");
    row->addStretch();
    row->addWidget(done);
    row->addWidget(cancel);
    lay->addLayout(row);

    connect(done, &QPushButton::clicked, this, [this]() { doFinish(); });
    connect(cancel, &QPushButton::clicked, this, [this]() { emit cancelled(); close(); });

    // 放在选区左下角
    QRect scr = QGuiApplication::primaryScreen()->geometry();
    double dpr = QGuiApplication::primaryScreen()->devicePixelRatio();
    int x = int(physRegion.left() / dpr);
    int y = int(physRegion.bottom() / dpr) + 8;
    if (y + height() > scr.bottom()) y = int(physRegion.top() / dpr) - height() - 8;
    if (x + width() > scr.right()) x = scr.right() - width();
    move(qMax(0, x), qMax(0, y));

    m_timer = new QTimer(this);
    connect(m_timer, &QTimer::timeout, this, [this]() { tick(); });
    m_timer->start(300);
    tick();
}

void LongShotBar::tick() {
    QImage frame = grabRegion(m_region);
    if (frame.isNull()) return;
    if (m_canvas.isNull()) {
        m_canvas = frame;
        m_prev = frame;
    } else {
        // 只有画面变化时才尝试拼接
        if (!m_prev.isNull() && frame.size() == m_prev.size()) {
            long long diff = 0;
            for (int y = 0; y < frame.height(); y += 8) {
                const QRgb* a = reinterpret_cast<const QRgb*>(frame.constScanLine(y));
                const QRgb* b = reinterpret_cast<const QRgb*>(m_prev.constScanLine(y));
                for (int x = 0; x < frame.width(); x += 8)
                    diff += std::abs(qGray(a[x]) - qGray(b[x]));
            }
            if (diff < 2000) return;   // 没变化
        }
        // 直接交给拼接器判断：没滚动/回滚/翻页 -> 帧里找不到画布底部内容 -> matched=false 自然丢弃。
        // （1.9.1 前这里先用 verticalShift 顶部模板预判方向，固定顶栏会让每帧都被误判为
        //   “没滚动/回滚”而丢弃——长截图一帧都拼不上；appendFrame 用底部模板不受顶栏影响，
        //   回滚帧同样匹配不上，预判是多余且有害的，已移除。）
        bool matched = false;
        QImage next = longshot::appendFrame(m_canvas, frame, &matched);
        if (matched) {
            m_canvas = next;
            m_dir = 0;                    // 竖向
            m_frames++;
            m_miss = 0;
        } else {
            ++m_miss;
            // 回滚仅作统计展示（verticalShift 顶部模板对固定顶栏不准，不影响拼接行为）
            const int dy = longshot::verticalShift(m_prev, frame);
            if (dy != INT_MIN && dy < -1) ++m_rolledBack;
            // 断档续接：连续 5 帧（约 1.5s）接不上且画面在变 -> 内容已超出可匹配范围
            // （一次滚过一整屏等），强制把当前帧接为新起点，避免此后永远停摆
            if (m_miss >= 5) {
                QImage out(m_canvas.width(), m_canvas.height() + frame.height(), m_canvas.format());
                QPainter p(&out);
                p.drawImage(0, 0, m_canvas);
                p.drawImage(0, m_canvas.height(), frame);
                p.end();
                m_canvas = out;
                ++m_gaps;
                m_miss = 0;
                m_frames++;
            }
        }
        m_prev = frame;
    }
    QString info = QStringLiteral("长截图：已拼接 %1 段（竖向） %2 x %3 px")
                       .arg(m_frames + 1).arg(m_canvas.width()).arg(m_canvas.height());
    if (m_rolledBack > 0)
        info += QStringLiteral(" · 已忽略 %1 次回滚").arg(m_rolledBack);
    if (m_gaps > 0)
        info += QStringLiteral(" · ⚠ 含 %1 处断档（滚动过快）").arg(m_gaps);
    m_info->setText(info);
    QImage thumb = m_canvas.scaledToHeight(28, Qt::SmoothTransformation);
    if (thumb.width() > 296) thumb = thumb.copy(thumb.width() - 296, 0, 296, thumb.height());
    m_preview->setPixmap(QPixmap::fromImage(thumb));
}

void LongShotBar::doFinish() {
    m_timer->stop();
    emit finished(m_canvas, m_gaps);
    close();
}

// ---------------- GIF 录制 ----------------
RecordBar::RecordBar(const QRect& physRegion, QWidget* parent)
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
