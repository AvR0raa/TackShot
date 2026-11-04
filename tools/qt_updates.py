import urllib.request, re

def raw(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "replace")

u = "https://download.qt.io/online/qtsdkrepository/windows_x86/desktop/qt6_683/Updates.xml"
try:
    x = raw(u)
    print("Updates.xml len", len(x))
    # print package names that mention mingw
    names = re.findall(r"<Name>([^<]+)</Name>", x)
    for n in names:
        if "mingw" in n.lower():
            print("  PKG:", n)
    # find one package block
    m = re.search(r"<PackageUpdate>(?:(?!</PackageUpdate>).)*mingw(?:(?!</PackageUpdate>).)*</PackageUpdate>", x, re.S)
    if m:
        block = m.group(0)
        print("\n--- sample package block (truncated) ---")
        print(block[:1800])
except Exception as e:
    print("ERR", e)
