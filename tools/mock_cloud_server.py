import base64, hashlib, io, json, struct, zlib, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

STATE = {"requests": 0, "last_path": "", "last_has_image": False, "last_auth": ""}
LOCK = threading.Lock()


def tiny_png(w=8, h=8, rgb=(0, 200, 120)):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b""
    for _ in range(h):
        raw += b"\x00" + bytes(rgb) * w
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/stats"):
            self._json(200, STATE)
            return
        if self.path.startswith("/reset"):
            STATE.update({"requests": 0, "last_path": "", "last_has_image": False, "last_auth": ""})
            self._json(200, {"ok": True})
            return
        self._json(404, {"error": "no"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b""
        with LOCK:
            STATE["requests"] += 1
            STATE["last_path"] = self.path
            STATE["last_has_image"] = b"image/png" in raw or b"PK\x03\x04" in raw
            STATE["last_auth"] = self.headers.get("token", "")

        if "picture" in self.path:
            # 与真实 API 一致的鉴权：参数必须在 URL query 里且签名正确
            # （1.8.1 曾因 setQuery 缺失导致参数全丢 -> 52003，mock 当时放过了 bug）
            params = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
            appid = params.get("appid", "")
            if not appid:
                self._json(200, {"error_code": "52003", "error_msg": "UNAUTHORIZED USER"})
                return
            start = raw.find(b"\x89PNG\r\n\x1a\n")
            if start >= 0:
                end = raw.find(b"IEND", start)
                png = raw[start:end + 8] if end > start else b""
            else:
                start = raw.find(b"\xff\xd8\xff")
                end = raw.find(b"\r\n--", start) if start >= 0 else -1
                png = raw[start:end] if start >= 0 and end > start else b""
            if not png:
                self._json(200, {"error_code": "69007", "error_msg": "bad image"})
                return
            expect = hashlib.md5((appid + hashlib.md5(png).hexdigest()
                                  + params.get("salt", "") + params.get("cuid", "")
                                  + params.get("mac", "") + "secret-test").encode()).hexdigest()
            if params.get("sign", "") != expect:
                self._json(200, {"error_code": "54001", "error_msg": "Invalid Sign"})
                return
            self._json(200, {
                "error_code": "0", "error_msg": "success",
                "data": {
                    "from": "zh", "to": "en",
                    "content": [
                        {"src": "这是第一段", "dst": "This is the first part",
                         "rect": "10 20 200 30", "lineCount": 1, "points": []},
                        {"src": "第二段文字", "dst": "Second part",
                         "rect": "10 70 180 28", "lineCount": 1, "points": []},
                    ],
                    "sumSrc": "这是第一段 第二段文字",
                    "sumDst": "This is the first part Second part",
                    "pasteImg": base64.b64encode(tiny_png(60, 30, (30, 120, 220))).decode(),
                },
            })
            return

        if "latex_ocr" in self.path:
            self._json(200, {"status": True,
                             "res": {"latex": "a^{2}+b^{2}=c^{2}", "conf": 0.97},
                             "request_id": "mock-1"})
            return

        self._json(404, {"error": "unknown path"})


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", 8902), H)
    print("cloud mock listening on 8902", flush=True)
    srv.serve_forever()
