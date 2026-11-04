import json, urllib.request, zipfile, io, os

d = json.load(urllib.request.urlopen("https://pypi.org/pypi/rapidocr_onnxruntime/json", timeout=60))
ver = d["info"]["version"]
print("rapidocr_onnxruntime", ver)
for u in d["urls"]:
    print("  ", u["filename"], round(u["size"]/1048576, 1), "MB")
url = [u for u in d["urls"] if u["filename"].endswith(".whl")][0]["url"]
data = urllib.request.urlopen(url, timeout=180).read()
print("downloaded", len(data))
out = r"C:\Users\laiki\.dsh\workspace\tackshot\toolchain\rapidocr"
os.makedirs(out, exist_ok=True)
with zipfile.ZipFile(io.BytesIO(data)) as z:
    names = z.namelist()
    print("entries:", len(names))
    models = [n for n in names if n.endswith((".onnx", ".txt", ".yaml")) and ("model" in n.lower() or "keys" in n.lower() or "dict" in n.lower())]
    for m in models[:20]:
        print("   ", m, z.getinfo(m).file_size)
    z.extractall(out)
print("extracted to", out)
