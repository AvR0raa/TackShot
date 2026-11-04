import urllib.request, re

def listing(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    return re.findall(r'href="([^"]+\.(?:7z|zip))"', html)

base = "https://download.qt.io/online/qtsdkrepository/windows_x86/desktop/"
for sub in ["qt6_683/qt.qt6.683.win64_mingw_131/", "tools_mingw1310/qt.tools.win64_mingw1310/"]:
    try:
        files = listing(base + sub)
        print("===", sub, len(files))
        for f in files:
            print("   ", f)
    except Exception as e:
        print("ERR", sub, e)
