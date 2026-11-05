import hashlib, json, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote

STATE = {"reqs": 0, "flaky": 0, "baidu_limit": 0}
LOCK = threading.Lock()

# 自检用的百度凭据（与 main.cpp --baidu-text-selftest 一致）
BAIDU_APPID = "20251105"
BAIDU_SECRET = "test-secret"

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/stats"):
            with LOCK:
                self._send(200, {"requests": STATE["reqs"]})
            return
        self._send(404, {"error": "no"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b""

        # 百度通用文本翻译（/api/trans/vip/translate 的表单协议）
        if self.path.startswith("/baidu"):
            self._baidu(raw)
            return

        try:
            req = json.loads(raw.decode("utf-8"))
        except Exception:
            req = {}

        with LOCK:
            STATE["reqs"] += 1
            seq = STATE["reqs"]

        system, user = "", ""
        for m in req.get("messages", []):
            if m.get("role") == "system":
                system = m.get("content", "")
            if m.get("role") == "user":
                user = m.get("content", "")

        if "bad" in self.path:
            self._send(401, {"error": {"message": "Invalid API key", "type": "auth_error"}})
            return
        if "flaky" in self.path:
            with LOCK:
                STATE["flaky"] += 1
                hit = STATE["flaky"]
            if hit <= 2:
                self._send(429, {"error": {"message": "rate limited"}})
                return
        if "limit" in self.path:
            self._send(402, {"error": {"message": "insufficient balance"}})
            return
        if "slow" in self.path:
            time.sleep(30)
        if "empty" in self.path:
            self._send(200, {"choices": [{"message": {"content": ""}}]})
            return

        marker = "GLOSSARY_OK|" if "术语表" in system else ""
        text = marker + ("你好，世界" if "Hello" in user or "hello" in user else ("【译】" + user[:40]))
        self._send(200, {
            "id": "mock-%d" % seq,
            "object": "chat.completion",
            "model": req.get("model", "mock"),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        })

    def _baidu(self, raw):
        """path 含 limit：首次返回 54003（触发客户端限流重试）；含 badsign：54001。
        其余校验 sign == md5(appid+q+salt+secret)，通过则逐行返回【中】前缀译文。"""
        with LOCK:
            STATE["reqs"] += 1
        # 手工解析表单：unquote 保留 '+'，两种空格编码风格都算签名候选
        pairs = {}
        for part in raw.decode("utf-8").split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                pairs[unquote(k)] = unquote(v)
        appid, q = pairs.get("appid", ""), pairs.get("q", "")
        salt, sign = pairs.get("salt", ""), pairs.get("sign", "")
        expects = {hashlib.md5((appid + x + salt + BAIDU_SECRET).encode("utf-8")).hexdigest()
                   for x in (q, q.replace("+", " "))}
        if "badsign" in self.path or sign not in expects:
            self._send(200, {"error_code": "54001", "error_msg": "Invalid Sign"})
            return
        if "limit" in self.path:
            with LOCK:
                STATE["baidu_limit"] += 1
                hit = STATE["baidu_limit"]
            if hit == 1:
                self._send(200, {"error_code": "54003", "error_msg": "Rate Limit Exceeded"})
                return
        # 与百度一致：trans_result 按非空行返回
        lines = [l for l in q.split("\n") if l != ""]
        self._send(200, {"from": "auto", "to": "zh",
                         "trans_result": [{"src": l, "dst": "【中】" + l} for l in lines]})

if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", 8899), H)
    print("mock listening on 8899", flush=True)
    srv.serve_forever()
