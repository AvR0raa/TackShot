import urllib.request, re

def links(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    h = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    return [x for x in re.findall(r'href="([^"]*)"', h)
            if not x.startswith(("/static", "http", "?")) and x not in ("..", ".")]

base = "https://download.qt.io/online/qtsdkrepository/windows_x86/desktop/"
for v in ["qt6_653/", "qt6_670/", "qt6_680/", "qt6_682/", "qt6_690/"]:
    try:
        ls = links(base + v)
        print("===", v, len(ls))
        for x in ls[:20]:
            print("   ", x)
    except Exception as e:
        print("ERR", v, e)
