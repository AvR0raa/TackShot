import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
# 只改第一处（--ocr-dialog-preview 区块）
old = """    int odIdx = args.indexOf("--ocr-dialog-preview");
    if (odIdx >= 0) {
        QString outPng = (odIdx + 1 < args.size()) ? args[odIdx + 1] : "ocrdialog.png";"""
new = """    int odlgIdx = args.indexOf("--ocr-dialog-preview");
    if (odlgIdx >= 0) {
        QString outPng = (odlgIdx + 1 < args.size()) ? args[odlgIdx + 1] : "ocrdialog.png";"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("renamed odIdx -> odlgIdx")
else:
    print("MISS")
