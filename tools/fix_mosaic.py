import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
old = "        if (m_current.type == Tool::Pen)\n            m_current.pts.append(local);"
new = "        if (m_current.type == Tool::Pen || m_current.type == Tool::Mosaic)\n            m_current.pts.append(local);"
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("mosaic freehand enabled")
else:
    print("MISS")
