import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("        QImage selfie = capture::captureRect(rect);",
              "        QImage selfie;\n        if (target) selfie = target->grabWindow(0).toImage();\n        if (selfie.isNull()) selfie = capture::captureRect(rect);")
io.open(p, "w", encoding="utf-8").write(s)
print("selfie via grabWindow")
