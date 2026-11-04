import json, time, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATE = {"reqs": 0, "flaky": 0}
LOCK = threading.Lock()

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

if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", 8899), H)
    print("mock listening on 8899", flush=True)
    srv.serve_forever()
