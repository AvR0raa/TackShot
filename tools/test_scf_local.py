# scf_main.py 本地事件级测试：模拟腾讯云函数 URL 的 event 结构直接调 main_handler。
# 用假凭据（打到百度/SimpleTex 会返回授权类错误，足以证明路由/签名/转发链路正确），
# 不消耗真实额度。
import base64, importlib.util, io, json, struct, sys, zlib

spec = importlib.util.spec_from_file_location("scf_main", __file__.replace("test_scf_local.py", "") + "..\\cloud\\scf_main.py")
scf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scf)


def tiny_png():
    w, h = 120, 40
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b""
    for _ in range(h):
        raw += b"\x00" + b"\x00" * w
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


import os
os.environ["BAIDU_APPID"] = "fakeappid000001"
os.environ["BAIDU_SECRET"] = "fakesecret"
os.environ["SIMPLETEX_TOKEN"] = "fake-uat"

fails = 0

# 1) /health（GET）
r = scf.main_handler({"httpMethod": "GET", "path": "/health", "queryString": "",
                      "headers": {}, "body": "", "isBase64Encoded": False}, None)
ok = r["statusCode"] == 200 and json.loads(r["body"])["ok"] is True
print("health:", "OK" if ok else "FAIL " + r["body"]); fails += 0 if ok else 1

# 2) /text（str body，函数 URL 文本路径）
r = scf.main_handler({"httpMethod": "POST", "path": "/text", "queryString": "",
                      "headers": {"content-type": "application/x-www-form-urlencoded"},
                      "body": "q=Hello, world&from=en&to=zh", "isBase64Encoded": False}, None)
o = json.loads(r["body"])
# 假凭据 -> 百度应返回 error_code（52003 未授权等），证明已打到百度
ok = "error_code" in o and o["error_code"] != 0
print("text:", "OK(baidu responded)" if ok else "FAIL", r["body"][:120]); fails += 0 if ok else 1

# 3) /picture（multipart 二进制，base64 通道）
png = tiny_png()
multipart = (b"--tackshotproxy\r\nContent-Disposition: form-data; name=\"image\"; "
             b"filename=\"t.png\"\r\nContent-Type: image/png\r\n\r\n" + png +
             b"\r\n--tackshotproxy--\r\n")
r = scf.main_handler({"httpMethod": "POST", "path": "/picture", "queryString": "from=auto&to=zh&paste=1",
                      "headers": {"content-type": "multipart/form-data; boundary=tackshotproxy"},
                      "body": base64.b64encode(multipart).decode(), "isBase64Encoded": True}, None)
o = json.loads(r["body"])
ok = "error_code" in o and o["error_code"] != 0
print("picture:", "OK(baidu responded)" if ok else "FAIL", r["body"][:120]); fails += 0 if ok else 1

# 3b) /picture latin-1 str 通道（网关把二进制按 str 塞的兜底路径）
r = scf.main_handler({"httpMethod": "POST", "path": "/picture", "queryString": "from=auto&to=zh&paste=1",
                      "headers": {},
                      "body": multipart.decode("latin-1"), "isBase64Encoded": False}, None)
o = json.loads(r["body"])
ok = "error_code" in o and o["error_code"] != 0
print("picture-latin1:", "OK(baidu responded)" if ok else "FAIL", r["body"][:120]); fails += 0 if ok else 1

# 3c) /picture 腾讯云真实格式：queryString 是解析好的 dict + JSON 协议（客户端现行协议）
json_body = json.dumps({"image": base64.b64encode(png).decode()})
r = scf.main_handler({"httpMethod": "POST", "path": "/picture",
                      "queryString": {"from": "auto", "to": "zh", "paste": "1"},
                      "headers": {"content-type": "application/json"},
                      "body": json_body, "isBase64Encoded": False}, None)
o = json.loads(r["body"])
ok = "error_code" in o and o["error_code"] != 0
print("picture-json:", "OK(baidu responded)" if ok else "FAIL", r["body"][:120]); fails += 0 if ok else 1

# 3d) /simpletex JSON 协议
r = scf.main_handler({"httpMethod": "POST", "path": "/simpletex",
                      "queryString": {"light": "1"},
                      "headers": {"content-type": "application/json"},
                      "body": json_body, "isBase64Encoded": False}, None)
o = json.loads(r["body"])
ok = o.get("status") is False or o.get("status") is True
print("simpletex-json:", "OK" if ok else "FAIL", r["body"][:100]); fails += 0 if ok else 1

# 4) /simpletex
r = scf.main_handler({"httpMethod": "POST", "path": "/simpletex", "queryString": "light=1",
                      "headers": {},
                      "body": base64.b64encode(multipart.replace(b'"image"', b'"file"')).decode(),
                      "isBase64Encoded": True}, None)
o = json.loads(r["body"])
ok = o.get("status") is False or (o.get("status") is True and "res" in o)  # 假token -> status false
print("simpletex:", "OK" if ok else "FAIL", r["body"][:120]); fails += 0 if ok else 1

# 5) 未知路由
r = scf.main_handler({"httpMethod": "POST", "path": "/nope", "queryString": "",
                      "headers": {}, "body": "", "isBase64Encoded": False}, None)
ok = r["statusCode"] == 404
print("404:", "OK" if ok else "FAIL"); fails += 0 if ok else 1

print("ALL:", "PASS" if fails == 0 else "%d FAIL" % fails)
sys.exit(1 if fails else 0)
