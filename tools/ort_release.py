import json, urllib.request
req = urllib.request.Request("https://api.github.com/repos/microsoft/onnxruntime/releases/latest",
                             headers={"User-Agent": "Mozilla/5.0"})
d = json.load(urllib.request.urlopen(req, timeout=60))
print("tag:", d["tag_name"])
for a in d["assets"]:
    n = a["name"]
    if "win-x64" in n and n.endswith(".zip"):
        print("%-50s %8.1f MB  %s" % (n, a["size"]/1048576, a["browser_download_url"]))
