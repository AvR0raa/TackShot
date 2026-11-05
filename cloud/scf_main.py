# TackShot 云代理 — 腾讯云函数 SCF 版（与 cloud/worker.js 等价）
# 密钥配置在 SCF 环境变量：BAIDU_APPID / BAIDU_SECRET / SIMPLETEX_TOKEN（可选 PROXY_KEY）
# 触发方式：函数 URL，路由与 Workers 版一致：/picture /text /simpletex /health
# 注意：SCF 的环境变量注入进程 os.environ（不在 context 上）
import hashlib, json, os, time, urllib.request
from urllib.parse import parse_qs

BAIDU_HOST = "https://fanyi-api.baidu.com"
SIMPLETEX_HOST = "https://server.simpletex.cn"


def main_handler(event, context):
    try:
        env = dict(os.environ)   # SCF 环境变量注入 os.environ，不在 context 上
        method = event.get("httpMethod", "POST")
        path = event.get("path", "/")
        # query 兼容三种事件格式：queryString 为 str / dict，或 queryStringParameters(dict)
        qs = {}
        raw_qs = event.get("queryString", "")
        if isinstance(raw_qs, dict):
            qs = {k: (v[0] if isinstance(v, list) else v) for k, v in raw_qs.items()}
        elif isinstance(event.get("queryStringParameters"), dict):
            qs = {k: (v[0] if isinstance(v, list) else v)
                  for k, v in event["queryStringParameters"].items()}
        elif raw_qs:
            qs = {k: v[0] for k, v in parse_qs(raw_qs).items()}
        headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}

        if method == "GET" and path == "/health":
            return resp(200, {"ok": True, "service": "tackshot-proxy"})
        if method != "POST":
            return resp(405, {"error": "method not allowed"})
        if env.get("PROXY_KEY") and headers.get("x-tackshot-key", "") != env["PROXY_KEY"]:
            return resp(403, {"error": "bad proxy key"})

        body = get_body(event)

        if path == "/picture":
            return relay_picture(event, headers, qs, env)
        if path == "/text":
            return relay_text(body, env)
        if path == "/simpletex":
            return relay_simpletex(event, qs, env)
        return resp(404, {"error": "unknown route"})
    except Exception as e:
        import traceback
        return resp(502, {"error": "proxy failure: %s" % e,
                          "tb": traceback.format_exc()[-600:]})


def relay_picture(event, headers, qs, env):
    # 首选 JSON 协议：{"image": "<base64>"}（函数 URL 对二进制 multipart 有损解码，必须走 base64）
    image = extract_image(event)
    if image is None:
        return resp(400, {"error_code": "69007", "error_msg": "image part missing",
                          "dbg": _dbg_body(event)})
    ctype = "image/jpeg" if image[:3] == b"\xff\xd8\xff" else "image/png"

    appid, secret = env["BAIDU_APPID"], env["BAIDU_SECRET"]
    salt = str(int(time.time() * 1000))
    cuid, mac = "APICUID", "mac"
    # sign = md5(appid + md5(image) + salt + cuid + mac + 密钥)
    sign = hashlib.md5((appid + hashlib.md5(image).hexdigest()
                        + salt + cuid + mac + secret).encode()).hexdigest()
    url = "%s/api/trans/sdk/picture?from=%s&to=%s&appid=%s&salt=%s&sign=%s" \
          "&cuid=%s&mac=%s&version=3&paste=%s" % (
        BAIDU_HOST, qs.get("from", "auto"), qs.get("to", "zh"),
        appid, salt, sign, cuid, mac, qs.get("paste", "1"))
    out = boundary_body({"image": ("tackshot.png", ctype, image)})
    return forward(url, out, "multipart/form-data; boundary=tackshotproxy")


def relay_text(body, env):
    form = {k: v[0] for k, v in parse_qs(body.decode("utf-8", "replace")).items()}
    qtext = form.get("q", "")
    if not qtext:
        return resp(400, {"error_code": "100", "error_msg": "empty q"})
    appid, secret = env["BAIDU_APPID"], env["BAIDU_SECRET"]
    salt = str(int(time.time() * 1000))
    sign = hashlib.md5((appid + qtext + salt + secret).encode()).hexdigest()
    out = ("q=%s" % _enc(qtext)).encode()
    url = "%s/api/trans/vip/translate?from=%s&to=%s&appid=%s&salt=%s&sign=%s" % (
        BAIDU_HOST, form.get("from", "auto"), form.get("to", "zh"), appid, salt, sign)
    return forward(url, out, "application/x-www-form-urlencoded")


def relay_simpletex(event, qs, env):
    image = extract_image(event)
    if image is None:
        return resp(400, {"status": False, "message": "file part missing",
                          "dbg": _dbg_body(event)})
    api = "/api/latex_ocr_turbo" if qs.get("light", "1") == "1" else "/api/latex_ocr"
    out = boundary_body({"file": ("tackshot.png", "image/png", image)})
    req = urllib.request.Request(SIMPLETEX_HOST + api, data=out, method="POST")
    req.add_header("Content-Type", "multipart/form-data; boundary=tackshotproxy")
    req.add_header("token", env.get("SIMPLETEX_TOKEN", ""))
    try:
        r = urllib.request.urlopen(req, timeout=60)
        return resp(r.status, json.loads(r.read().decode("utf-8", "replace")))
    except urllib.error.HTTPError as e:
        return resp(e.code, {"status": False, "message": e.read().decode("utf-8", "replace")[:200]})


# ---------------- helpers ----------------
def get_body(event):
    """事件 body -> bytes。函数 URL：文本 body 是 str，二进制走 base64（isBase64Encoded）。"""
    body = event.get("body")
    if body is None:
        return b""
    if isinstance(body, dict):
        raise RuntimeError("event.body 是 dict —— 请到函数 URL 设置里关闭「参数兼容」开关")
    if event.get("isBase64Encoded"):
        import base64
        return base64.b64decode(body)
    if isinstance(body, bytes):
        return body
    return body.encode("utf-8", "surrogateescape")


def get_body_binary(event):
    """二进制场景（图片）：依次尝试 raw bytes / latin-1 str / 无标志 base64。"""
    b = get_body(event)
    if _has_magic(b):
        return b
    body = event.get("body")
    if isinstance(body, str):
        alt = body.encode("latin-1", "ignore")
        if _has_magic(alt):
            return alt
        # 兜底：body 是 base64 文本但事件没带 isBase64Encoded 标志
        import base64 as _b64
        try:
            dec = _b64.b64decode(body.strip(), validate=False)
            if _has_magic(dec):
                return dec
        except Exception:
            pass
    return b


def _has_magic(b):
    return b"\x89PNG" in b or b"\xff\xd8\xff" in b


def extract_image(event):
    """从事件提取图片字节。首选 JSON {"image": base64}（无损）；
    兜底 multipart 魔数定位（供支持二进制的网关，如 Workers/本地）。"""
    import base64
    body = get_body(event)
    # JSON 协议
    try:
        j = json.loads(body.decode("utf-8", "replace"))
        if isinstance(j, dict) and j.get("image"):
            data = base64.b64decode(j["image"])
            if _has_magic(data):
                return data
    except Exception:
        pass
    # multipart 兜底
    b = get_body_binary(event)
    start = b.find(b"\x89PNG\r\n\x1a\n")
    jpeg = b.find(b"\xff\xd8\xff")
    if jpeg >= 0 and (start < 0 or jpeg < start):
        start = jpeg
    if start < 0:
        return None
    end = b.find(b"\r\n--", start)
    return b[start:end if end > start else len(b)]


def _dbg_body(event):
    """part-missing 时的事件摘要，用于线上定位 SCF 事件格式（不含敏感信息）。"""
    body = event.get("body")
    return {"bodyType": type(body).__name__,
            "bodyLen": len(body) if body is not None else -1,
            "isB64": event.get("isBase64Encoded"),
            "bodyHead": repr(body)[:200] if body is not None else None,
            "qsType": type(event.get("queryString")).__name__,
            "keys": sorted(event.keys())}


def _enc(s):
    import urllib.parse
    return urllib.parse.quote(s, safe="")


def boundary_body(parts):
    b = "tackshotproxy"
    out = b""
    for name, (fn, ctype, data) in parts.items():
        out += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
                "Content-Type: %s\r\n\r\n" % (b, name, fn, ctype)).encode()
        out += data + b"\r\n"
    out += ("--%s--\r\n" % b).encode()
    return out


def forward(url, data, ctype):
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", ctype)
    try:
        r = urllib.request.urlopen(req, timeout=60)
        return resp(r.status, json.loads(r.read().decode("utf-8", "replace")))
    except urllib.error.HTTPError as e:
        return resp(e.code, {"error": e.read().decode("utf-8", "replace")[:200]})


def resp(status, obj):
    return {"isBase64Encoded": False, "statusCode": status,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(obj, ensure_ascii=False)}
