import urllib.request, re

def links(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    h = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    return [x for x in re.findall(r'href="([^"]*\.7z)"', h)]

base = "https://download.qt.io/online/qtsdkrepository/windows_x86/desktop/qt6_683/qt6_683/qt.qt6.683.win64_mingw/"
try:
    fs = links(base)
    print("files:", len(fs))
    for f in fs:
        print("  ", f)
except Exception as e:
    print("ERR", e)
