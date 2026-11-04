import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\longshot.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("#include <QPainter>", "#include <QPainter>\n#include <QTransform>")
s = s.replace("""    QImage c = canvas.transposed();
    QImage f = frame.transposed();
    QImage r = appendFrame(c, f, matched);
    return r.transposed();""",
"""    QTransform tr(0, 1, 1, 0, 0, 0);   // 转置：x<->y
    QImage c = canvas.transformed(tr);
    QImage f = frame.transformed(tr);
    QImage r = appendFrame(c, f, matched);
    return r.transformed(tr);""")
io.open(p, "w", encoding="utf-8").write(s)
print("transpose fixed")
