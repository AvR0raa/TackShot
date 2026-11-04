import io

# build: winmm
p = r"C:\Users\laiki\.dsh\workspace\tackshot\tools\build.ps1"
s = io.open(p, encoding="utf-8").read()
s = s.replace('"-lmfplat","-lmfreadwrite","-lmfuuid","-lpropsys","-lshlwapi",',
              '"-lmfplat","-lmfreadwrite","-lmfuuid","-lpropsys","-lshlwapi","-lwinmm",')
io.open(p, "w", encoding="utf-8").write(s)

# main.cpp: 音频自检
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace('#include "mfrec.h"', '#include "mfrec.h"\n#include "audiocap.h"\n#include <windows.h>\n#include <mmsystem.h>')

anchor = "    // MP4 录制自检：录制屏幕左上角 640x360，固定秒数"
code = """    // 音频自检：播放 1kHz 音调 -> 系统回环采集 -> 直接写 MP4（含 AAC）
    int auIdx = args.indexOf("--audio-selftest");
    if (auIdx >= 0) {
        QString out = (auIdx + 1 < args.size()) ? args[auIdx + 1] : "audio.mp4";
        double seconds = (auIdx + 2 < args.size()) ? args[auIdx + 2].toDouble() : 3.0;

        // 生成 1kHz 正弦 WAV（16bit/48k/立体声）
        QString wavPath = QDir::tempPath() + "/tackshot_tone.wav";
        {
            const int rate = 48000, ch = 2, secs = 5;
            QByteArray pcm;
            pcm.resize(rate * ch * 2 * secs);
            qint16* p = reinterpret_cast<qint16*>(pcm.data());
            for (int i = 0; i < rate * secs; ++i) {
                qint16 v = qint16(12000 * qSin(2.0 * M_PI * 1000.0 * i / rate));
                p[i * 2] = v; p[i * 2 + 1] = v;
            }
            QFile wf(wavPath);
            if (wf.open(QIODevice::WriteOnly)) {
                auto w32 = [&](quint32 v) { wf.write(reinterpret_cast<const char*>(&v), 4); };
                auto w16 = [&](quint16 v) { wf.write(reinterpret_cast<const char*>(&v), 2); };
                wf.write("RIFF", 4); w32(36 + pcm.size()); wf.write("WAVE", 4);
                wf.write("fmt ", 4); w32(16); w16(1); w16(ch); w32(rate); w32(rate * ch * 2); w16(ch * 2); w16(16);
                wf.write("data", 4); w32(pcm.size()); wf.write(pcm);
                wf.close();
            }
        }
        PlaySoundW(reinterpret_cast<LPCWSTR>(wavPath.utf16()), nullptr, SND_FILENAME | SND_ASYNC | SND_LOOP);

        Mp4Recorder rec;
        QString err;
        bool okOpen = rec.open(out, 640, 360, 15, 4000, true, 48000, 2);

        AudioCapture mic;
        bool micOk = mic.start(AudioCapture::SystemLoopback);

        int frames = 0;
        qint64 audioBytes = 0;
        double sumSq = 0.0;
        long long nSamples = 0;
        int peak = 0;
        QElapsedTimer t; t.start();
        while (t.elapsed() < seconds * 1000 && okOpen && micOk) {
            QImage part = capture::captureRect(QRect(0, 0, 640, 360));
            if (!part.isNull()) { rec.writeFrame(part); frames++; }
            QByteArray pcm = mic.read();
            if (!pcm.isEmpty()) {
                rec.writeAudio(pcm);
                audioBytes += pcm.size();
                const qint16* s16 = reinterpret_cast<const qint16*>(pcm.constData());
                int n = pcm.size() / 2;
                for (int i = 0; i < n; ++i) {
                    int v = s16[i];
                    peak = qMax(peak, qAbs(v));
                    sumSq += double(v) * v;
                    nSamples++;
                }
            }
            QThread::msleep(66);
        }
        bool ok = okOpen ? rec.close() : false;
        PlaySoundW(nullptr, nullptr, 0);
        mic.stop();

        QFile rf(out + ".txt");
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts << "open=" << (okOpen ? "true" : "false") << " capture=" << (micOk ? "true" : "false") << "\\n";
            if (!micOk) ts << "captureError=" << mic.lastError() << "\\n";
            if (!okOpen) ts << "openError=" << rec.lastError() << "\\n";
            ts << "frames=" << frames << " audioBytes=" << audioBytes << "\\n";
            ts << "rms=" << (nSamples ? qSqrt(sumSq / nSamples) : 0.0)
               << " peak=" << peak << "\\n";
            ts << "bytes=" << QFileInfo(out).size() << "\\n";
            rf.close();
        }
        QFile::remove(wavPath);
        return ok || micOk ? 0 : 11;
    }

"""
if anchor in s:
    s = s.replace(anchor, code + anchor, 1)
    s = s.replace("#include <QFont>", "#include <QFont>\n#include <QtMath>")
    io.open(p, "w", encoding="utf-8").write(s)
    print("audio selftest added")
else:
    print("MISS")
