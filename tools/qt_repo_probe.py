import urllib.request, re, json, os

def get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

targets = [
 "https://download.qt.io/online/qtsdkrepository/windows_x86/desktop/qt6_683/",
 "https://download.qt.io/online/qtsdkrepository/windows_x86/desktop/tools_mingw1310/",
]
for u in targets:
    try:
        html = get(u).decode("utf-8", "replace")
        links = re.findall(r'href="([^"]+)"', html)
        print("===", u, len(links), "links")
        for l in links:
            if "/" in l and not l.startswith("?") and not l.startswith(".."):
                print("   ", l)
    except Exception as e:
        print("ERR", u, type(e).__name__, e)
