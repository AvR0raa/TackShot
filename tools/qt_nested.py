import urllib.request, re

def links(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    h = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    return [x for x in re.findall(r'href="([^"]*)"', h)
            if not x.startswith(("/static", "http", "?")) and x not in ("..", ".")]

base = "https://download.qt.io/online/qtsdkrepository/windows_x86/desktop/"
for p in ["qt6_683/qt6_683/", "qt6_680/qt6_680/", "qt6_690/qt6_690/"]:
    try:
        ls = links(base + p)
        print("===", p, len(ls))
        mingw = [x for x in ls if "mingw" in x.lower() and "src" not in x.lower()]
        for x in mingw[:12]:
            print("   MINGW:", x)
        if not mingw:
            for x in ls[:12]: print("   ", x)
    except Exception as e:
        print("ERR", p, e)

print()
try:
    ls = links(base)
    tools = sorted(set(x for x in ls if x.startswith("tools_mingw")))
    print("toolchain dirs:", tools)
except Exception as e:
    print("ERR tools", e)
