import os, collections

def rd_varint(b, i):
    v = 0; s = 0
    while True:
        c = b[i]; i += 1
        v |= (c & 0x7f) << s; s += 7
        if not (c & 0x80): return v, i

def parse(b):
    i = 0; out = []; n = len(b)
    while i < n:
        try: key, i = rd_varint(b, i)
        except IndexError: break
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
            out.append(("BAD", wt, None)); break
    return out

root = r"C:\Users\laiki\.dsh\workspace\tackshot\models"
for fn in ["2478d3813bea9afacf7fee18abb09d45.onnx", "94186d8ad4eacc8b8aaf3c1088eb9353.onnx"]:
    b = open(os.path.join(root, fn), "rb").read()
    top = parse(b)
    print("==", fn, "top fields:", [(f, wt) for f, wt, v in top])
    g = [v for f, wt, v in top if f == 7][0]
    gp = parse(g)
    print("   graph fields:", collections.Counter(f for f, wt, v in gp))
    for f, wt, v in gp:
        if f in (11, 12, 13) and wt == 2:
            s = v[:40]
            print("     field", f, "->", s.hex(" "), "|", "".join(chr(c) if 32 <= c < 127 else "." for c in s))
            break
    print("   tail of graph:", g[-40:].hex(" "))
