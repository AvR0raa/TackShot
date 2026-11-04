import os, struct, subprocess, sys, shutil

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

# 归档格式: [u32 count] { [u32 pathBytes][UTF-16LE path][u32 size][u32 offset] } [data...]
index = bytearray()
blobs = bytearray()
data_off = 0
for rel, full in files:
    raw = open(full, "rb").read()
    p = rel.encode("utf-16-le")
    index += struct.pack("<I", len(p)) + p + struct.pack("<II", len(raw), data_off)
    blobs += raw
    data_off += len(raw)

header = struct.pack("<I", len(files)) + bytes(index)
payload = header + bytes(blobs)
open(os.path.join(BUILD, "payload.bin"), "wb").write(payload)
print("files=%d payload=%d" % (len(files), len(payload)))
