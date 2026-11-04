import os, struct, shutil

WS = r"C:\Users\laiki\.dsh\workspace\tackshot"
BUILD = os.path.join(WS, "build")
exe = os.path.join(BUILD, "TackShotSetup.exe")
rcc = os.path.join(BUILD, "payload.rcc")

data = open(exe, "rb").read()
payload = open(rcc, "rb").read()
offset = len(data)
blob = data + payload + b"TSPAYLOAD1" + struct.pack("<II", offset, len(payload))
open(exe, "wb").write(blob)
print("exe=%d payload=%d total=%d" % (offset, len(payload), len(blob)))

# 分发目录
dist = os.path.join(WS, "dist")
shutil.copy2(exe, os.path.join(dist, "TackShotSetup.exe"))
# setup 运行需要 Qt 运行库，直接复用 dist/TackShot 的部署
for f in os.listdir(os.path.join(dist, "TackShot")):
    if f.startswith("Qt6") and f.endswith(".dll"):
        shutil.copy2(os.path.join(dist, "TackShot", f), os.path.join(dist, f))
for f in ["libgcc_s_seh-1.dll", "libstdc++-6.dll", "libwinpthread-1.dll"]:
    p = os.path.join(dist, "TackShot", f)
    if os.path.exists(p):
        shutil.copy2(p, os.path.join(dist, f))
print("dist ready:", os.listdir(dist))
