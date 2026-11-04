import zlib, struct, os, math

W = H = 64
px = bytearray()

def lerp(a, b, t): return a + (b - a) * t

for y in range(H):
    for x in range(W):
        # rounded rect mask
        r = 14
        cx = min(max(x, r), W - 1 - r)
        cy = min(max(y, r), H - 1 - r)
        d = math.hypot(x - cx, y - cy)
        inside = d <= r
        if not inside:
            px += bytes([0, 0, 0, 0])
            continue
        t = (x + y) / (W + H) * 2
        rr = lerp(0x3d, 0x1f, t); gg = lerp(0x7b, 0x4f, t); bb = lerp(0xfd, 0xd0, t)
        # crosshair
        col = (int(rr), int(gg), int(bb), 255)
        dx, dy = x - 32, y - 32
        # circle ring
        dist = math.hypot(dx, dy)
        if 7.0 <= dist <= 9.5:
            col = (255, 255, 255, 255)
        # diagonal lines
        if abs(dx - dy) < 1.6 and (abs(dx) > 9 or abs(dy) > 9):
            col = (255, 255, 255, 255)
        if abs(dx + dy) < 1.6 and (abs(dx) > 9 or abs(dy) > 9):
            col = (255, 255, 255, 255)
        px += bytes(col)

raw = b""
for y in range(H):
    raw += b"\x00" + bytes(px[y * W * 4:(y + 1) * W * 4])

def chunk(tag, data):
    c = struct.pack(">I", len(data)) + tag + data
    return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

png = b"\x89PNG\r\n\x1a\n"
png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
png += chunk(b"IDAT", zlib.compress(raw, 9))
png += chunk(b"IEND", b"")

ico = struct.pack("<HHH", 0, 1, 1)
ico += struct.pack("<BBBBHHII", W, H, 0, 0, 1, 32, len(png), 22)
ico += png

root = r"C:\Users\laiki\.dsh\workspace\tackshot"
os.makedirs(os.path.join(root, "res"), exist_ok=True)
open(os.path.join(root, "res", "tackshot.ico"), "wb").write(ico)
open(os.path.join(root, "res", "tackshot.png"), "wb").write(png)
print("ico bytes:", len(ico), "png:", len(png))
