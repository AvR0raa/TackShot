import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()

s = s.replace('#include "audiocap.h"', '#include "audiocap.h"\n#include <mfapi.h>\n#include <mfidl.h>\n#include <mfreadwrite.h>\n#include <mferror.h>')

anchor = "    // 译图自检：合成带文字的图"
code = r'''    // 录制方向自检：录 1 秒 -> 用 MF 解码首帧 -> 与原始抓屏比对（正向 / 上下翻转哪个更像）
    int oriIdx = args.indexOf("--record-orientation-selftest");
    if (oriIdx >= 0) {
        QString outMp4 = (oriIdx + 1 < args.size()) ? args[oriIdx + 1] : "ori.mp4";
        QString report = (oriIdx + 2 < args.size()) ? args[oriIdx + 2] : (outMp4 + ".txt");
        const QRect region(0, 0, 640, 360);

        QImage expected = capture::captureRect(region);
        Mp4Recorder rec;
        if (!rec.open(outMp4, region.width(), region.height(), 15, 8000, false)) {
            QFile rf(report);
            if (rf.open(QIODevice::WriteOnly)) rf.write(QString("open failed: %1\n").arg(rec.lastError()).toUtf8());
            return 16;
        }
        for (int i = 0; i < 12; ++i) {
            QImage f = capture::captureRect(region);
            if (!f.isNull()) rec.writeFrame(f);
            QThread::msleep(66);
        }
        rec.close();

        // 解码首帧
        MFStartup(MF_VERSION, MFSTARTUP_NOSOCKET);
        QImage decoded;
        {
            IMFSourceReader* reader = nullptr;
            HRESULT hr = MFCreateSourceReaderFromURL(reinterpret_cast<LPCWSTR>(outMp4.utf16()),
                                                     nullptr, &reader);
            if (SUCCEEDED(hr) && reader) {
                IMFMediaType* outType = nullptr;
                MFCreateMediaType(&outType);
                outType->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Video);
                outType->SetGUID(MF_MT_SUBTYPE, MFVideoFormat_RGB32);
                reader->SetCurrentMediaType(0, nullptr, outType);
                outType->Release();

                IMFMediaType* cur = nullptr;
                UINT32 tw = 0, th = 0;
                if (SUCCEEDED(reader->GetCurrentMediaType(0, &cur)) && cur) {
                    MFGetAttributeSize(cur, MF_MT_FRAME_SIZE, &tw, &th);
                    cur->Release();
                }
                DWORD streamIndex = 0, flags = 0;
                LONGLONG ts = 0;
                IMFSample* sample = nullptr;
                for (int k = 0; k < 30 && !sample; ++k) {
                    if (FAILED(reader->ReadSample(0, 0, &streamIndex, &flags, &ts, &sample))) break;
                    if (flags & MF_SOURCE_READERF_ENDOFSTREAM) break;
                    if (sample && !(flags & MF_SOURCE_READERF_CURRENTMEDIATYPECHANGED)) break;
                    if (sample) { sample->Release(); sample = nullptr; }
                }
                if (sample) {
                    IMFMediaBuffer* buf = nullptr;
                    if (SUCCEEDED(sample->ConvertToContiguousBuffer(&buf)) && buf) {
                        BYTE* data = nullptr; DWORD len = 0;
                        if (SUCCEEDED(buf->Lock(&data, nullptr, &len)) && tw && th) {
                            decoded = QImage(int(tw), int(th), QImage::Format_RGB32);
                            const int stride = int(tw) * 4;
                            for (UINT32 y = 0; y < th; ++y)
                                memcpy(decoded.scanLine(int(y)), data + size_t(y) * stride, size_t(stride));
                            buf->Unlock();
                        }
                        buf->Release();
                    }
                    sample->Release();
                }
                reader->Release();
            }
        }
        MFShutdown();

        auto meanDiff = [](const QImage& a, const QImage& b) -> double {
            if (a.isNull() || b.isNull() || a.size() != b.size()) return 9999.0;
            long long s = 0, n = 0;
            for (int y = 0; y < a.height(); y += 4) {
                const QRgb* la = reinterpret_cast<const QRgb*>(a.constScanLine(y));
                const QRgb* lb = reinterpret_cast<const QRgb*>(b.constScanLine(y));
                for (int x = 0; x < a.width(); x += 4) {
                    s += qAbs(qGray(la[x]) - qGray(lb[x]));
                    n++;
                }
            }
            return n ? double(s) / n : 9999.0;
        };

        QImage flipped = decoded.mirrored(false, true);
        double dNorm = meanDiff(decoded, expected);
        double dFlip = meanDiff(flipped, expected);
        bool upright = dNorm < dFlip;

        QFile rf(report);
        if (rf.open(QIODevice::WriteOnly)) {
            QTextStream ts(&rf);
            ts.setEncoding(QStringConverter::Utf8);
            ts << "decoded=" << decoded.width() << "x" << decoded.height() << "\n";
            ts << "diffNormal=" << dNorm << " diffFlipped=" << dFlip << "\n";
            ts << "upright=" << (upright ? "true" : "false") << "\n";
            rf.close();
        }
        if (!decoded.isNull()) decoded.save(outMp4 + ".frame.png");
        return upright ? 0 : 17;
    }

'''
if anchor in s:
    s = s.replace(anchor, code + anchor, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("orientation selftest added")
else:
    print("MISS")
