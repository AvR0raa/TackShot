import os

def rd_varint(b, i):
    v = 0; s = 0
    while True:
        c = b[i]; i += 1
        v |= (c & 0x7f) << s; s += 7
        if not (c & 0x80): return v, i

root = r"C:\Users\laiki\.dsh\workspace\tackshot\models"
fn = sorted(f for f in os.listdir(root) if f.endswith(".onnx"))[0]
b = open(os.path.join(root, fn), "rb").read()
print(fn, len(b), b[:16].hex(" "))
i = 0
for step in range(8):
    key, j = rd_varint(b, i)
    f, wt = key >> 3, key & 7
    print("  @%d key=0x%02x field=%d wt=%d" % (i, key, f, wt))
    if wt == 0:
        v, i = rd_varint(b, j); print("     varint", v)
    elif wt == 2:
        ln, k = rd_varint(b, j); print("     len", ln, "data", b[k:k+8].hex(" "))
        i = k + ln
    else:
        print("     unexpected"); break
    if i >= len(b): print("  end"); break
