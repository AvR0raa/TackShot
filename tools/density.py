import os
root = r"C:\Users\laiki\.dsh\workspace\tackshot\models"
src = r"C:\Users\laiki\AppData\Local\Programs\PixPin\model"
KEY = b"wsK&56aeSk!Rn7Lb"

def density(b):
    if not b: return 0
    return sum(1 for c in b if 32 <= c < 127) / len(b)

for fn in os.listdir(src):
    if not fn.endswith(".bin"): continue
    raw = open(os.path.join(src, fn), "rb").read()
    n = len(raw)
    k = (KEY * (n // len(KEY) + 1))[:n]
    dec = (int.from_bytes(raw, "big") ^ int.from_bytes(k, "big")).to_bytes(n, "big")
    print("\n==", fn, n)
    step = max(1, n // 10)
    for i in range(0, n, step):
        seg_r = raw[i:i+step]; seg_d = dec[i:i+step]
        print("   %7d  raw=%.2f  dec=%.2f" % (i, density(seg_r), density(seg_d)))
