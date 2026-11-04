import struct, sys

def check_gif(path):
    d = open(path, "rb").read()
    assert d[:6] in (b"GIF89a", b"GIF87a"), "bad magic"
    w, h = struct.unpack("<HH", d[6:10])
    flags = d[10]
    gct = bool(flags & 0x80)
    gct_size = 2 ** ((flags & 7) + 1)
    p = 13 + (3 * gct_size if gct else 0)
    frames = 0
    delays = []
    while p < len(d):
        b = d[p]
        if b == 0x3B:
            p += 1
            break
        if b == 0x21:
            label = d[p+1]; p += 2
            if label == 0xF9:
                size = d[p]; p += 1
                delays.append(struct.unpack("<H", d[p+1:p+3])[0])
                p += size
                p += 1  # terminator
            else:
                while d[p] != 0:
                    p += d[p] + 1
                p += 1
        elif b == 0x2C:
            frames += 1
            p += 10
            lflags = d[p-1]
            if lflags & 0x80:
                p += 3 * (2 ** ((lflags & 7) + 1))
            p += 1  # lzw min code size
            while d[p] != 0:
                p += d[p] + 1
            p += 1
        else:
            print("unexpected byte", hex(b), "at", p); break
    print("size=%dx%d frames=%d delays=%s gct=%s trailing=%s" % (w, h, frames, delays[:4], gct, p == len(d)))

check_gif(r"C:\Users\laiki\.dsh\workspace\tackshot\build\giftest.gif")
