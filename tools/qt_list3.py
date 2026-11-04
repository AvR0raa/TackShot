import urllib.request, re
req = urllib.request.Request("https://download.qt.io/online/qtsdkrepository/windows_x86/desktop/", headers={"User-Agent": "Mozilla/5.0"})
h = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
hrefs = re.findall(r'href="([^"]*)"', h)
qt6 = sorted(set(x for x in hrefs if "qt6" in x.lower()))
print("qt6 dirs:", len(qt6))
for x in qt6: print("  ", x)
