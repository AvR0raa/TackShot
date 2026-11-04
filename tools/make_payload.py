import os, sys, subprocess

WS = r"C:\Users\laiki\.dsh\workspace\tackshot"
DIST = os.path.join(WS, "dist", "TackShot")
BUILD = os.path.join(WS, "build")
os.makedirs(BUILD, exist_ok=True)

files = []
for root, dirs, fns in os.walk(DIST):
    for fn in fns:
        full = os.path.join(root, fn)
        rel = os.path.relpath(full, DIST).replace("\\", "/")
        files.append((rel, full))
files.sort()

qrc = ['<RCC>', '  <qresource prefix="/payload">']
for rel, full in files:
    qrc.append('    <file alias="%s">%s</file>' % (rel, full.replace("\\", "/")))
qrc += ['  </qresource>', '</RCC>']
qrc_path = os.path.join(BUILD, "payload.qrc")
open(qrc_path, "w", encoding="utf-8").write("\n".join(qrc))
print("qrc files:", len(files))

rcc = os.path.join(WS, "toolchain", "bin", "rcc.exe")
out = os.path.join(BUILD, "payload.rcc")
if os.path.exists(out):
    os.remove(out)
r = subprocess.run([rcc, "--binary", "-o", out, qrc_path])
print("rcc exit:", r.returncode, "size:", os.path.getsize(out) if os.path.exists(out) else -1)
