import urllib.request, os, time
WS = r"C:\Users\laiki\.dsh\workspace\tackshot"
DL = os.path.join(WS, "dl"); os.makedirs(DL, exist_ok=True)
url = "https://github.com/microsoft/onnxruntime/releases/download/v1.31.1/onnxruntime-win-x64-1.31.1.zip"
dst = os.path.join(DL, "onnxruntime.zip")
if os.path.exists(dst) and os.path.getsize(dst) > 10_000_000:
    print("exists", os.path.getsize(dst)); raise SystemExit
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
t0 = time.time(); total = 0
with urllib.request.urlopen(req, timeout=300) as r, open(dst + ".part", "wb") as f:
    while True:
        c = r.read(1 << 20)
        if not c: break
        f.write(c); total += len(c)
        if total % (20 << 20) < (1 << 20): print("... %d MB" % (total >> 20), flush=True)
os.replace(dst + ".part", dst)
print("OK %.1f MB %.1fs" % (total / 1048576, time.time() - t0))
