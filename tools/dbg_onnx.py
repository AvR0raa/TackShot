import os

def rd_varint(b, i):
    v = 0; s = 0
    while True:
        c = b[i]; i += 1
        v |= (c & 0x7f) << s; s += 7
        if not (c & 0x80): return v, i

def parse(b, limit=None):
    i = 0; out = []; n = len(b)
    while i < n:
        try:
            key, i = rd_varint(b, i)
        except IndexError:
            break
        f, wt = key >> 3, key & 7
        if wt == 0:
            v, i = rd_varint(b, i); out.append((f, 0, v))
        elif wt == 2:
            ln, i = rd_varint(b, i)
            if i + ln > n: ln = n - i
            out.append((f, 2, b[i:i+ln])); i += ln
        elif wt == 5: out.append((f, 5, b[i:i+4])); i += 4
        elif wt == 1: out.append((f, 1, b[i:i+8])); i += 8
        else:
            out.append((f, wt, None)); break
        if limit and len(out) > limit: break
    return out

root = r"C:\Users\laiki\.dsh\workspace\tackshot\models"
for fn in sorted(os.listdir(root)):
    if not fn.endswith(".onnx"): continue
    b = open(os.path.join(root, fn), "rb").read()
    top = parse(b, 12)
    print(fn, len(b), "top:", [(f, wt, (v if wt == 0 else len(v))) for f, wt, v in top][:8])
    g = [v for f, wt, v in top if f == 7]
    if g:
        gp = parse(g[0], 12)
        print("   graph fields:", [(f, wt, (v if wt == 0 else len(v))) for f, wt, v in gp][:8])
    break
