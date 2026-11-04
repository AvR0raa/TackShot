import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\mfrec.cpp"
s = io.open(p, encoding="utf-8").read()
old = """        QImage s = src.convertToFormat(QImage::Format_RGB32);
        for (int y = 0; y < m_h; ++y)
            memcpy(dst + size_t(y) * stride, s.constScanLine(y), size_t(m_w) * 4);"""
new = """        QImage s = src.convertToFormat(QImage::Format_RGB32);
        // Media Foundation 的 RGB32 输入是 bottom-up（DIB 约定），逐行倒序拷贝
        for (int y = 0; y < m_h; ++y)
            memcpy(dst + size_t(m_h - 1 - y) * stride, s.constScanLine(y), size_t(m_w) * 4);"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("video flip fixed")
else:
    print("MISS flip")
