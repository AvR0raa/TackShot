import urllib.request, re

def raw(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")

base = "https://download.qt.io/online/qtsdkrepository/windows_x86/desktop/"
for sub in ["qt6_683/", "qt6_683/qt.qt6.683.win64_mingw_131/", "qt6_683/qt.qt6.683.win64_mingw/", ""]:
    try:
        h = raw(base + sub)
        hrefs = re.findall(r'href="([^"]*)"', h)
        hrefs = [x for x in hrefs if not x.startswith(("/static", "http", "?")) and x not in ("..", ".")]
        print("===", repr(sub), "->", len(hrefs))
        for x in hrefs[:40]:
            print("    ", x)
    except Exception as e:
        print("ERR", repr(sub), e)
