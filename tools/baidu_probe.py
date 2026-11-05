# 百度图片翻译端点/签名探测：定位 V2.0(picture2) 的正确调用方式
# 只读用户凭据（DPAPI 解密），发送合成 "Hello" 测试图
import base64, ctypes, ctypes.wintypes as wt, hashlib, json, struct, zlib, os, sys
from urllib.parse import urlencode
import urllib.request, uuid

DATA_DIR = os.environ.get("TACKSHOT_DATA_DIR",
                          os.path.join(os.environ["LOCALAPPDATA"], "TackShot"))

def dpapi_decrypt(blob):
    class BLOB(ctypes.Structure):
        _fields_ = [("cb", wt.DWORD), ("pb", ctypes.POINTER(ctypes.c_byte))]
    buf = ctypes.create_string_buffer(blob, len(blob))
    pin = BLOB(len(blob), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))
    pout = BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(pin), None, None, None, None, 1, ctypes.byref(pout)):
        raise OSError("CryptUnprotectData failed")
    out = ctypes.string_at(pout.pb, pout.cb)
    ctypes.windll.kernel32.LocalFree(pout.pb)
    return out

cfg = json.load(open(os.path.join(DATA_DIR, "config.json"), encoding="utf-8"))
sec_json = json.load(open(os.path.join(DATA_DIR, "secrets.dat"), encoding="utf-8"))
appid = cfg["baiduAppId"]
secret = dpapi_decrypt(base64.b64decode(sec_json["baidu_secret"])).decode("utf-8")
print("appId=%s secret=present(%d chars)" % (appid, len(secret)))

# 合成 400x120 PNG："Hello"
def make_png():
    W, H = 400, 120
    px = bytearray(b"\xff" * (W * H * 3))
    # 简易 5x7 字模画个黑方块即可，服务端只需要可识别内容——直接用大黑条纹
    for y in range(30, 90):
        for x in range(60, 340):
            if (x // 20) % 2 == 0:
                o = (y * W + x) * 3
                px[o] = px[o + 1] = px[o + 2] = 0
    raw = b""
    for y in range(H):
        raw += b"\x00" + bytes(px[y * W * 3:(y + 1) * W * 3])
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))

png = make_png()
md5img = hashlib.md5(png).hexdigest()
salt = uuid.uuid4().hex[:16]

def boundary_post(url, params, png, field="image"):
    b = "----tackshotprobe"
    body = b""
    for k, v in params.items():
        body += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
                 % (b, k, v)).encode()
    body += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"t.png\"\r\n"
             "Content-Type: image/png\r\n\r\n" % (b, field)).encode()
    body += png + b"\r\n--%s--\r\n" % b.encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "multipart/form-data; boundary=" + b})
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return r.status, r.read()[:400].decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400].decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)

def try_case(name, endpoint, sign_mode, params_where):
    cuid, mac = "APICUID", "mac"
    if sign_mode == "v1":
        sign = hashlib.md5((appid + md5img + salt + cuid + mac + secret).encode()).hexdigest()
        base = {"from": "auto", "to": "zh", "appid": appid, "salt": salt, "sign": sign,
                "cuid": cuid, "mac": mac, "version": "3", "paste": "1"}
    else:  # v2 猜测：不带 cuid/mac
        sign = hashlib.md5((appid + md5img + salt + secret).encode()).hexdigest()
        base = {"from": "auto", "to": "zh", "appid": appid, "salt": salt, "sign": sign,
                "version": "3", "paste": "1"}
    if params_where == "query":
        url = endpoint + "?" + urlencode(base)
        st, body = boundary_post(url, {}, png)
    else:
        st, body = boundary_post(endpoint, base, png)
    print("%-38s -> %s %s" % (name, st, body.replace("\n", " ")[:220]))

HOST = "https://fanyi-api.baidu.com"
for ep in [HOST + "/api/trans/sdk/picture", HOST + "/api/trans/sdk/picture2"]:
    for mode in ["v1", "v2"]:
        for where in ["query", "form"]:
            try_case("%s sign=%s params=%s" % (ep.split("/")[-1], mode, where), ep, mode, where)
