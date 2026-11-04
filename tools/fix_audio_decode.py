import io

# 1) 音频：去掉 EVENTCALLBACK（我们是轮询，不设置事件句柄会让 Start 失败）
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\audiocap.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("""    DWORD flags = AUDCLNT_STREAMFLAGS_EVENTCALLBACK;
    if (src == SystemLoopback) flags |= AUDCLNT_STREAMFLAGS_LOOPBACK;""",
"""    DWORD flags = 0;   // 轮询模式即可，不注册事件回调
    if (src == SystemLoopback) flags |= AUDCLNT_STREAMFLAGS_LOOPBACK;""")
io.open(p, "w", encoding="utf-8").write(s)
print("audio flags fixed")

# 2) 解码自检：记录 HRESULT，读更多次
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("""            IMFSourceReader* reader = nullptr;
            HRESULT hr = MFCreateSourceReaderFromURL(reinterpret_cast<LPCWSTR>(outMp4.utf16()),
                                                     nullptr, &reader);
            if (SUCCEEDED(hr) && reader) {""",
"""            IMFSourceReader* reader = nullptr;
            HRESULT hr = MFCreateSourceReaderFromURL(reinterpret_cast<LPCWSTR>(outMp4.utf16()),
                                                     nullptr, &reader);
            qint64 hrOpen = hr;
            if (SUCCEEDED(hr) && reader) {""")
s = s.replace("""                reader->SetCurrentMediaType(0, nullptr, outType);
                outType->Release();""",
"""                HRESULT hrSet = reader->SetCurrentMediaType(0, nullptr, outType);
                outType->Release();
                qint64 hrSetVal = hrSet;""")
s = s.replace("""                for (int k = 0; k < 30 && !sample; ++k) {
                    if (FAILED(reader->ReadSample(0, 0, &streamIndex, &flags, &ts, &sample))) break;
                    if (flags & MF_SOURCE_READERF_ENDOFSTREAM) break;
                    if (sample && !(flags & MF_SOURCE_READERF_CURRENTMEDIATYPECHANGED)) break;
                    if (sample) { sample->Release(); sample = nullptr; }
                }""",
"""                qint64 lastHr = 0;
                for (int k = 0; k < 60 && !sample; ++k) {
                    HRESULT rs = reader->ReadSample(0, 0, &streamIndex, &flags, &ts, &sample);
                    lastHr = rs;
                    if (FAILED(rs)) break;
                    if (flags & MF_SOURCE_READERF_ENDOFSTREAM) break;
                    if (sample) break;
                }
                hrDecode = lastHr;""")
s = s.replace("""        MFStartup(MF_VERSION, MFSTARTUP_NOSOCKET);
        QImage decoded;""",
"""        MFStartup(MF_VERSION, MFSTARTUP_NOSOCKET);
        QImage decoded;
        qint64 hrOpen = 0, hrSetVal = 0, hrDecode = 0;
        UINT32 tw = 0, th = 0;""")
s = s.replace("""                IMFMediaType* cur = nullptr;
                UINT32 tw = 0, th = 0;""",
"""                IMFMediaType* cur = nullptr;""")
s = s.replace("""            ts << "decoded=" << decoded.width() << "x" << decoded.height() << "\\n";""",
"""            ts << "hrOpen=" << hrOpen << " hrSetType=" << hrSetVal << " hrRead=" << hrDecode
               << " size=" << tw << "x" << th << "\\n";
            ts << "decoded=" << decoded.width() << "x" << decoded.height() << "\\n";""")
io.open(p, "w", encoding="utf-8").write(s)
print("decode diagnostics added")
