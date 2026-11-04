import os

def rd_varint(b, i):
    v = 0; s = 0
    while True:
        c = b[i]; i += 1
        v |= (c & 0x7f) << s; s += 7
        if not (c & 0x80): return v, i

def walk(b, label, base=0):
    i = 0; n = len(b); cnt = 0
    while i < n:
        try: key, j = rd_varint(b, i)
        except IndexError: return ("eof", i)
        f, wt = key >> 3, key & 7
        if wt == 0:
            v, i = rd_varint(b, j)
        elif wt == 2:
            ln, k = rd_varint(b, j)
            if k + ln > n:
                return ("overflow", i)
            i = k + ln
        elif wt == 5: i = j + 4
        elif wt == 1: i = j + 8
        else:
            return ("bad wt=%d field=%d" % (wt, f), i)
        cnt += 1
    return ("ok", i)

root = r"C:\Users\laiki\.dsh\workspace\tackshot\models"
b = open(os.path.join(root, "94186d8ad4eacc8b8aaf3c1088eb9353.onnx"), "rb").read()
top = []
i = 0
n = len(b)
while i < n:
    key, j = rd_varint(b, i)
    f, wt = key >> 3, key & 7
    if wt == 2:
        ln, k = rd_varint(b, j)
        top.append((f, k, ln))
        i = k + ln
    elif wt == 0:
        v, i = rd_varint(b, j); top.append((f, j, v))
    else:
        top.append(("bad", i, wt)); break
print("top:", [(f, off, ln) for f, off, ln in top][:6])
g_off, g_len = [t for t in top if t[0] == 7][0][1], [t for t in top if t[0] == 7][0][2]
g = b[g_off:g_off+g_len]
print("graph off=%d len=%d" % (g_off, g_len))
res, off = walk(g, "graph")
print("graph walk:", res, "at graph+%d (file+%d)" % (off, g_off + off))
print("hex around:", g[max(0,off-8):off+16].hex(" "))
print("file size:", len(b), "graph end:", g_off + g_len, "trailing:", len(b) - (g_off + g_len))
