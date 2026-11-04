import urllib.request, os, time

WS = r"C:\Users\laiki\.dsh\workspace\tackshot"
DL = os.path.join(WS, "dl")
os.makedirs(DL, exist_ok=True)

Q = "https://download.qt.io/online/qtsdkrepository/windows_x86/desktop/qt6_683/qt6_683/qt.qt6.683.win64_mingw/"
T = "https://download.qt.io/online/qtsdkrepository/windows_x86/desktop/tools_mingw1310/qt.tools.win64_mingw1310/"

items = [
    (Q + "6.8.3-0-202503201308qtbase-Windows-Windows_10_22H2-Mingw-Windows-Windows_10_22H2-X86_64.7z", "qtbase.7z"),
    (Q + "6.8.3-0-202503201308qtsvg-Windows-Windows_10_22H2-Mingw-Windows-Windows_10_22H2-X86_64.7z", "qtsvg.7z"),
    (Q + "6.8.3-0-202503201308qttools-Windows-Windows_10_22H2-Mingw-Windows-Windows_10_22H2-X86_64.7z", "qttools.7z"),
    (T + "13.1.0-202407240918mingw1310.7z", "mingw1310.7z"),
]

for url, name in items:
    dst = os.path.join(DL, name)
    if os.path.exists(dst) and os.path.getsize(dst) > 1024 * 1024:
        print("skip %-14s %d" % (name, os.path.getsize(dst)), flush=True)
        continue
    t0 = time.time()
    print("GET", name, flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    total = 0
    with urllib.request.urlopen(req, timeout=180) as r, open(dst + ".part", "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
            if total % (20 << 20) < (1 << 20):
                print("   ... %d MB" % (total >> 20), flush=True)
    os.replace(dst + ".part", dst)
    print("OK %-14s %10d bytes %.1fs" % (name, total, time.time() - t0), flush=True)

print("ALL DONE", flush=True)
