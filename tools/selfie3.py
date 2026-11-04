import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("""        ov->show();
        QCoreApplication::processEvents();
        QThread::msleep(600);
        QCoreApplication::processEvents();""",
"""        ov->show();
        ov->setWindowOpacity(1.0);   // 自拍时跳过淡入动画，确保内容真的画出来
        QCoreApplication::processEvents();
        QThread::msleep(600);
        QCoreApplication::processEvents();""")
io.open(p, "w", encoding="utf-8").write(s)
print("opacity forced")
