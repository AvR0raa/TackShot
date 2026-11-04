import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()

s = s.replace("""            IMFSourceReader* reader = nullptr;
            HRESULT hr = MFCreateSourceReaderFromURL(reinterpret_cast<LPCWSTR>(outMp4.utf16()),
                                                     nullptr, &reader);""",
"""            IMFSourceReader* reader = nullptr;
            IMFAttributes* attrs = nullptr;
            MFCreateAttributes(&attrs, 1);
            if (attrs) attrs->SetUINT32(MF_SOURCE_READER_ENABLE_VIDEO_PROCESSING, TRUE);
            HRESULT hr = MFCreateSourceReaderFromURL(reinterpret_cast<LPCWSTR>(outMp4.utf16()),
                                                     attrs, &reader);
            if (attrs) attrs->Release();""")
s = s.replace("""            ts << "hrOpen=" << hrOpen""",
"""            ts << "fileSize=" << QFileInfo(outMp4).size() << "\\n";
            ts << "hrOpen=" << hrOpen""")
io.open(p, "w", encoding="utf-8").write(s)
print("video processing attribute added")
