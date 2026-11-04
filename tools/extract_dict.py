import struct, os, json

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
        else: break
    return out

p = r"C:\Users\laiki\.dsh\workspace\tackshot\toolchain\rapidocr\rapidocr_onnxruntime\models\ch_PP-OCRv4_rec_infer.onnx"
b = open(p, "rb").read()
top = parse(b)
meta = {}
for f, wt, v in top:
    if f == 14 and wt == 2:
        kv = {}
        for f2, wt2, v2 in parse(v):
            if f2 == 1: kv["k"] = v2.decode("utf-8", "replace")
            if f2 == 2: kv["v"] = v2.decode("utf-8", "replace")
        if "k" in kv and "v" in kv:
            meta[kv["k"]] = kv["v"]
print("metadata keys:", list(meta.keys()))
for k, v in meta.items():
    print("  %-14s len=%d  head=%r" % (k, len(v), v[:60]))

if "character" in meta:
    chars = meta["character"].splitlines()
    print("chars:", len(chars), chars[:5], chars[-5:])
    out = r"C:\Users\laiki\.dsh\workspace\tackshot\models\ppocr_keys_v1.txt"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(chars))
    print("saved", out, os.path.getsize(out))
