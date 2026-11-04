import os, struct

WS = r"C:\Users\laiki\.dsh\workspace\tackshot"
B = os.path.join(WS, "build")
exe = os.path.join(B, "TackShotSetup.exe")
payload = open(os.path.join(B, "payload.bin"), "rb").read()
data = open(exe, "rb").read()
offset = len(data)
out = data + payload + b"TSPAYLD1" + struct.pack("<II", offset, len(payload))

dist = os.path.join(WS, "dist")
os.makedirs(dist, exist_ok=True)

targets = ["TackShotSetup.exe", "TackShotSetup-1.6.exe"]
written = None
for name in targets:
    p = os.path.join(dist, name)
    try:
        with open(p, "wb") as f:
            f.write(out)
        written = p
        break
    except PermissionError:
        print("locked, trying next name:", name)
        continue

if written is None:
    p = os.path.join(dist, "TackShotSetup-1.6.exe")
    with open(p, "wb") as f:
        f.write(out)
    written = p

print("stub=%d payload=%d total=%.1fMB -> %s" % (offset, len(payload), len(out) / 1048576, written))
