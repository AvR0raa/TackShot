import struct, sys

def boxes(data, start, end, depth=0, want=None):
    out = []
    p = start
    while p + 8 <= end:
        size, typ = struct.unpack(">I4s", data[p:p+8])
        hdr = 8
        if size == 1:
            size = struct.unpack(">Q", data[p+8:p+16])[0]; hdr = 16
        elif size == 0:
            size = end - p
        if size < hdr: break
        out.append((typ.decode("latin1"), p, size, hdr))
        p += size
    return out

data = open(sys.argv[1], "rb").read()
print("file size", len(data))
top = boxes(data, 0, len(data))
print("top boxes:", [(t, s) for t, p, s, h in top])

def find(path):
    cur = [(0, len(data))]
    node = None
    for name in path:
        nxt = []
        for (s, e) in cur:
            for t, p, sz, h in boxes(data, s, e):
                if t == name:
                    nxt.append((p + h, p + sz))
                    node = (p, sz)
        cur = nxt
        if not cur: return None
    return cur

moov = [b for b in top if b[0] == "moov"]
if not moov:
    print("NO moov"); sys.exit(1)
mp, msz, mh = moov[0][1], moov[0][2], moov[0][3]
mchildren = boxes(data, mp + mh, mp + msz)
print("moov children:", [t for t, p, s, h in mchildren])

# mvhd
for t, p, sz, h in mchildren:
    if t == "mvhd":
        ver = data[p+h]
        if ver == 0:
            timescale, duration = struct.unpack(">II", data[p+h+12:p+h+20])
        else:
            timescale, duration = struct.unpack(">I", data[p+h+20:p+h+24])[0], struct.unpack(">Q", data[p+h+24:p+h+32])[0]
        print("timescale=%d duration=%d -> %.2fs" % (timescale, duration, duration / timescale))

for t, p, sz, h in mchildren:
    if t == "trak":
        kids = boxes(data, p+h, p+sz)
        print(" trak:", [k[0] for k in kids])
        mdia = [k for k in kids if k[0] == "mdia"]
        if not mdia: continue
        mdp, mdsz, mdh = mdia[0][1], mdia[0][2], mdia[0][3]
        for t2, p2, sz2, h2 in boxes(data, mdp+mdh, mdp+mdsz):
            if t2 == "minf":
                for t3, p3, sz3, h3 in boxes(data, p2+h2, p2+sz2):
                    if t3 == "stbl":
                        for t4, p4, sz4, h4 in boxes(data, p3+h3, p3+sz3):
                            if t4 == "stsd":
                                entry = data[p4+h4+8+4:p4+h4+8+8]
                                # visual sample entry: 8+70 bytes after entry header
                                w, hh = struct.unpack(">HH", data[p4+h4+8+24+8:p4+h4+8+24+12])
                                print("   codec=%s  %dx%d" % (entry.decode("latin1"), w, hh))
                            if t4 == "stsz":
                                cnt = struct.unpack(">I", data[p4+h4+8:p4+h4+12])[0]
                                print("   samples=%d" % cnt)
                            if t4 == "stts":
                                n = struct.unpack(">I", data[p4+h4+4:p4+h4+8])[0]
                                print("   stts entries=%d" % n)
