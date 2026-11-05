import base64, json, struct, threading, zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

# 客户端托管协议：图片走 JSON {"image": "<base64>"}（网关对二进制 multipart 有损解码）

# TackShot 云代理 mock：模拟 cloud/worker.js 的三个路由。
# 关键断言数据：客户端走托管模式时【不应】发送任何凭据（appid/sign/salt/token）。
STATE = {"requests": 0, "last_had_creds": None, "last_route": ""}
LOCK = threading.Lock()


def tiny_png(w=60, h=30, rgb=(30, 120, 220)):
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
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/stats"):
            with LOCK:
                self._json(200, STATE)
            return
        self._json(404, {"error": "no"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b""
        route = urlparse(self.path).path
        qs = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}

        # 断言：托管请求不得携带任何凭据
        had_creds = bool(qs.get("appid") or qs.get("sign") or qs.get("salt")
                         or self.headers.get("token"))

        # JSON {"image": base64} 或 multipart 两种形态都取图（PNG/JPG 均可）
        def _ok_img(b):
            return b"\x89PNG" in b or b"\xff\xd8\xff" in b

        img_ok = _ok_img(raw)
        try:
            j = json.loads(raw.decode("utf-8", "replace"))
            if isinstance(j, dict) and j.get("image"):
                img_ok = _ok_img(base64.b64decode(j["image"]))
        except Exception:
            pass

        with LOCK:
            STATE["requests"] += 1
            STATE["last_had_creds"] = had_creds
            STATE["last_route"] = route

        if route == "/picture":
            if not img_ok:
                self._json(200, {"error_code": "69007", "error_msg": "no image"})
                return
            self._json(200, {"error_code": "0", "error_msg": "success", "data": {
                "from": "auto", "to": "zh",
                "content": [
                    {"src": "Proxy line one", "dst": "代理行一",
                     "rect": "5 10 200 30", "lineCount": 1, "points": []},
                    {"src": "Proxy line two", "dst": "代理行二",
                     "rect": "5 60 200 30", "lineCount": 1, "points": []},
                ],
                "sumSrc": "Proxy line one Proxy line two",
                "sumDst": "代理行一 代理行二",
                "pasteImg": base64.b64encode(tiny_png()).decode(),
            }})
            return

        if route == "/text":
            form = {k: v[0] for k, v in parse_qs(raw.decode("utf-8", "replace")).items()}
            if not form.get("q"):
                self._json(200, {"error_code": "100", "error_msg": "empty q"})
                return
            self._json(200, {"from": "auto", "to": "zh",
                             "trans_result": [{"src": l, "dst": "【代】" + l}
                                              for l in form["q"].split("\n") if l]})
            return

        if route == "/simpletex":
            if not img_ok:
                self._json(200, {"status": False, "message": "no file"})
                return
            self._json(200, {"status": True,
                             "res": {"latex": "E = m c^{2}", "conf": 0.96},
                             "request_id": "proxy-mock-1"})
            return

        self._json(404, {"error": "unknown route"})


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", 8903), H)
    print("proxy mock listening on 8903", flush=True)
    srv.serve_forever()
