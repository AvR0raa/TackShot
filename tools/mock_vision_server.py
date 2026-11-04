#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在线视觉识别的本地 mock 服务（仅用 Python 标准库）。

用法：
    python tools/mock_vision_server.py [--port 8901]

端点（POST 到 .../chat/completions）：
    /v1/ok/chat/completions      -> 200，content 为 "识别结果 OK"
    /v1/array/chat/completions   -> 200，content 为数组（验证分段拼接）
    /v1/bad/chat/completions     -> 401（Key 无效，不应重试）
    /v1/noretry/chat/completions -> 403（无权限，不应重试）
    /v1/flaky/chat/completions   -> 前 2 次 500，第 3 次成功（验证 5xx 重试）
    /v1/busy/chat/completions    -> 恒定 429（验证重试次数上限）
    /v1/slow/chat/completions    -> 睡眠 10s 后返回（验证客户端超时）

    GET /stats -> {"requests": N, "lastHasImage": true/false}
                  其中 lastHasImage 表示最近一次请求是否真的带上了 base64 图片。
    GET /reset -> {"ok": true}，清零计数（含 /v1/flaky 的失败计数），便于反复测试。
"""

import argparse
import base64
import json
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATE = {"requests": 0, "lastHasImage": False, "flaky": 0}
LOCK = threading.Lock()


def find_image_url(req):
    """取出 messages 里第一段 data:image/... 的图片 URL，没有则返回空串。"""
    for m in req.get("messages", []):
        content = m.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") != "image_url":
                continue
            url = (part.get("image_url") or {}).get("url", "")
            if isinstance(url, str) and url.startswith("data:image/") and ";base64," in url:
                return url
    return ""


def png_size(data_url):
    """只解 PNG 头（IHDR）拿到宽高，用于验证客户端确实缩放到了 1600 以内。"""
    try:
        b64 = data_url.split(",", 1)[1][:80]
        while len(b64) % 4:
            b64 += "="
        raw = base64.b64decode(b64)
        if raw[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        w, h = struct.unpack(">II", raw[16:24])
        return w, h
    except Exception:
        return None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except OSError:
            pass  # 客户端已超时断开（/v1/slow 的正常现象），无需报错

    def _error(self, code, message):
        self._send(code, {"error": {"message": message, "type": "mock_error"}})

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")
        if path == "/stats":
            with LOCK:
                stats = {"requests": STATE["requests"], "lastHasImage": STATE["lastHasImage"]}
            self._send(200, stats)
            return
        if path == "/reset":
            with LOCK:
                STATE.update({"requests": 0, "lastHasImage": False, "flaky": 0})
            self._send(200, {"ok": True})
            return
        self._error(404, "unknown path: %s" % self.path)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        try:
            req = json.loads(raw.decode("utf-8"))
            if not isinstance(req, dict):
                req = {}
        except Exception:
            req = {}

        image_url = find_image_url(req)
        has_img = bool(image_url)

        with LOCK:
            STATE["requests"] += 1
            seq = STATE["requests"]
            STATE["lastHasImage"] = has_img

        size = png_size(image_url) if has_img else None
        size_txt = "%dx%d" % size if size else "-"
        path = self.path.split("?")[0]
        print("[%d] POST %s image=%s png=%s bytes=%d"
              % (seq, path, has_img, size_txt, len(raw)), flush=True)

        if not path.rstrip("/").endswith("/chat/completions"):
            self._error(404, "expected /chat/completions")
            return

        mode = ""
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2 and parts[-2:] == ["chat", "completions"]:
            # /v1/<mode>/chat/completions -> 取 <mode>；/v1/chat/completions 视为默认
            mode = parts[-3] if len(parts) >= 4 else ""

        if mode == "bad":
            self._error(401, "Invalid API key")
            return
        if mode == "noretry":
            self._error(403, "Permission denied")
            return
        if mode == "busy":
            self._error(429, "Too many requests")
            return
        if mode == "flaky":
            with LOCK:
                STATE["flaky"] += 1
                hit = STATE["flaky"]
            if hit <= 2:
                self._error(500, "upstream temporarily unavailable")
                return
            self._reply_ok(seq, req, "识别结果 OK")
            return
        if mode == "slow":
            time.sleep(10)
            self._reply_ok(seq, req, "识别结果 OK")
            return
        if mode == "array":
            self._send(200, {
                "id": "mock-%d" % seq,
                "object": "chat.completion",
                "model": req.get("model", "mock"),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": "识别结果"},
                            {"type": "text", "text": " OK"},
                        ],
                    },
                    "finish_reason": "stop",
                }],
            })
            return
        if mode == "ok" or mode == "":
            self._reply_ok(seq, req, "识别结果 OK")
            return

        self._error(404, "unknown mode: %s" % mode)

    def _reply_ok(self, seq, req, text):
        self._send(200, {
            "id": "mock-%d" % seq,
            "object": "chat.completion",
            "model": req.get("model", "mock"),
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        })


def main():
    ap = argparse.ArgumentParser(description="TackShot 视觉识别 mock 服务")
    ap.add_argument("--port", type=int, default=8901, help="监听端口，默认 8901")
    ap.add_argument("--host", default="127.0.0.1", help="监听地址，默认 127.0.0.1")
    args = ap.parse_args()

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print("mock vision server on http://%s:%d" % (args.host, args.port), flush=True)
    print("  POST /v1/ok/chat/completions  -> 识别结果 OK", flush=True)
    print("  GET  /stats                   -> {requests:N,lastHasImage:bool}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
