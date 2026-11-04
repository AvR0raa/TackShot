import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\overlay.cpp"
s = io.open(p, encoding="utf-8").read()
if "static QRect physRegionOf" not in s:
    s = s.replace("void Overlay::onLongShot() {",
"""static QRect physRegionOf(const QRect& physBase, const QRect& sel) {
    return QRect(physBase.topLeft() + sel.topLeft(), sel.size());
}

void Overlay::onLongShot() {""", 1)
io.open(p, "w", encoding="utf-8").write(s)
print("helper restored")
