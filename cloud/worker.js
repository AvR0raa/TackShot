// TackShot 云代理 — Cloudflare Workers 版
// 密钥只存在 Workers 环境变量里（BAIDU_APPID / BAIDU_SECRET / SIMPLETEX_TOKEN），
// 客户端只持有本 Worker 的 URL，百度密钥永不进入安装包。
//
// 路由（与客户端 src/managed.cpp 约定一致；图片走 JSON+base64，兼容 multipart）：
//   GET  /health                     探活
//   POST /picture?from=&to=&paste=   JSON{"image":b64} -> 百度图片翻译（代理补签名）
//   POST /text                       form(q,from,to)  -> 百度通用文本翻译（代理补签名）
//   POST /simpletex?light=1          JSON{"image":b64} -> SimpleTex 公式识别（代理补 token）
//
// 部署：wrangler deploy（或控制台粘贴本文件），然后设置环境变量：
//   wrangler secret put BAIDU_APPID
//   wrangler secret put BAIDU_SECRET
//   wrangler secret put SIMPLETEX_TOKEN
// 可选：wrangler secret put PROXY_KEY   // 设置后客户端必须带 x-tackshot-key 头（止损开关）

const BAIDU_HOST = "https://fanyi-api.baidu.com";
const SIMPLETEX_HOST = "https://server.simpletex.cn";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    try {
      if (request.method === "GET" && url.pathname === "/health")
        return json({ ok: true, service: "tackshot-proxy" });
      if (request.method !== "POST")
        return json({ error: "method not allowed" }, 405);
      if (env.PROXY_KEY && request.headers.get("x-tackshot-key") !== env.PROXY_KEY)
        return json({ error: "bad proxy key" }, 403);

      if (url.pathname === "/picture") return relayPicture(request, url, env);
      if (url.pathname === "/text") return relayText(request, url, env);
      if (url.pathname === "/simpletex") return relaySimpleTex(request, url, env);
      return json({ error: "unknown route" }, 404);
    } catch (e) {
      return json({ error: "proxy failure: " + e.message }, 502);
    }
  },
};

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// 协议：JSON {"image": "<base64>"}（无损，首选）或 multipart(image)
async function readImageBytes(request, partName) {
  const ctype = (request.headers.get("content-type") || "").toLowerCase();
  if (ctype.includes("application/json")) {
    const j = await request.json().catch(() => null);
    if (j && j.image) {
      const bin = atob(String(j.image));
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      return bytes;
    }
    return null;
  }
  const form = await request.formData();
  const part = form.get(partName);
  if (!part || typeof part === "string") return null;
  return new Uint8Array(await part.arrayBuffer());
}

async function relayPicture(request, url, env) {
  const bytes = await readImageBytes(request, "image");
  if (!bytes || !bytes.length)
    return json({ error_code: "69007", error_msg: "image part missing" }, 400);

  const appid = env.BAIDU_APPID, secret = env.BAIDU_SECRET;
  const salt = String(Date.now());
  const cuid = "APICUID", mac = "mac";
  // sign = md5(appid + md5(image) + salt + cuid + mac + 密钥)
  const sign = md5(appid + md5Bytes(bytes) + salt + cuid + mac + secret);

  const q = new URLSearchParams({
    from: url.searchParams.get("from") || "auto",
    to: url.searchParams.get("to") || "zh",
    appid, salt, sign, cuid, mac, version: "3",
    paste: url.searchParams.get("paste") || "1",
  });

  const out = new FormData();
  out.append("image", new Blob([bytes], { type: "image/png" }), "tackshot.png");
  const resp = await fetch(`${BAIDU_HOST}/api/trans/sdk/picture?${q}`,
                           { method: "POST", body: out });
  return new Response(resp.body, {
    status: resp.status,
    headers: { "Content-Type": resp.headers.get("Content-Type") || "application/json" },
  });
}

async function relayText(request, _url, env) {
  const form = await request.formData();
  const qtext = form.get("q") || "";
  const from = form.get("from") || "auto";
  const to = form.get("to") || "zh";
  if (!qtext) return json({ error_code: "100", error_msg: "empty q" }, 400);

  const appid = env.BAIDU_APPID, secret = env.BAIDU_SECRET;
  const salt = String(Date.now());
  // sign = md5(appid + q + salt + 密钥)，q 为原文（未 URL 编码）
  const sign = md5(appid + qtext + salt + secret);

  const body = new URLSearchParams({ q: qtext, from, to, appid, salt, sign });
  const resp = await fetch(`${BAIDU_HOST}/api/trans/vip/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });
  return new Response(resp.body, {
    status: resp.status,
    headers: { "Content-Type": resp.headers.get("Content-Type") || "application/json" },
  });
}

async function relaySimpleTex(request, url, env) {
  const bytes = await readImageBytes(request, "file");
  if (!bytes || !bytes.length)
    return json({ status: false, message: "file part missing" }, 400);

  const api = (url.searchParams.get("light") || "1") === "1"
    ? "/api/latex_ocr_turbo" : "/api/latex_ocr";
  const out = new FormData();
  out.append("file", new Blob([bytes], { type: "image/png" }), "tackshot.png");
  const resp = await fetch(SIMPLETEX_HOST + api, {
    method: "POST",
    headers: { token: env.SIMPLETEX_TOKEN || "" },
    body: out,
  });
  return new Response(resp.body, {
    status: resp.status,
    headers: { "Content-Type": resp.headers.get("Content-Type") || "application/json" },
  });
}

// ---------------- 纯 JS MD5（Workers 原生 crypto 不支持 MD5；标准 RFC1321 移植） ----------------
function md5(s) {
  return hex(md5raw(new TextEncoder().encode(s)));
}
function md5Bytes(bytes) {
  return hex(md5raw(bytes));
}
function md5raw(bytes) {
  const n = bytes.length;
  const state = [1732584193, -271733879, -1732584194, 271733878];
  let i;
  for (i = 64; i <= n; i += 64)
    md5cycle(state, md5blk(bytes, i - 64));
  const tail = new Array(16).fill(0);
  const rest = bytes.subarray(i - 64);
  for (i = 0; i < rest.length; i++)
    tail[i >> 2] |= rest[i] << ((i % 4) << 3);
  tail[i >> 2] |= 0x80 << ((i % 4) << 3);
  if (i > 55) {
    md5cycle(state, tail);
    tail.fill(0);
  }
  tail[14] = n * 8;
  md5cycle(state, tail);
  return state;
}
function md5blk(bytes, pos) {
  const blks = new Array(16);
  for (let i = 0; i < 16; i++) {
    const o = pos + i * 4;
    blks[i] = bytes[o] + (bytes[o + 1] << 8) + (bytes[o + 2] << 16) + (bytes[o + 3] << 24);
  }
  return blks;
}
function hex(state) {
  let s = "";
  for (let i = 0; i < 4; i++)
    for (let j = 0; j < 4; j++)
      s += ((state[i] >>> (j * 8)) & 0xff).toString(16).padStart(2, "0");
  return s;
}
function md5cycle(x, blk) {
  let [a, b, c, d] = x;
  a = ff(a, b, c, d, blk[0], 7, -680876936);
  d = ff(d, a, b, c, blk[1], 12, -389564586);
  c = ff(c, d, a, b, blk[2], 17, 606105819);
  b = ff(b, c, d, a, blk[3], 22, -1044525330);
  a = ff(a, b, c, d, blk[4], 7, -176418897);
  d = ff(d, a, b, c, blk[5], 12, 1200080426);
  c = ff(c, d, a, b, blk[6], 17, -1473231341);
  b = ff(b, c, d, a, blk[7], 22, -45705983);
  a = ff(a, b, c, d, blk[8], 7, 1770035416);
  d = ff(d, a, b, c, blk[9], 12, -1958414417);
  c = ff(c, d, a, b, blk[10], 17, -42063);
  b = ff(b, c, d, a, blk[11], 22, -1990404162);
  a = ff(a, b, c, d, blk[12], 7, 1804603682);
  d = ff(d, a, b, c, blk[13], 12, -40341101);
  c = ff(c, d, a, b, blk[14], 17, -1502002290);
  b = ff(b, c, d, a, blk[15], 22, 1236535329);

  a = gg(a, b, c, d, blk[1], 5, -165796510);
  d = gg(d, a, b, c, blk[6], 9, -1069501632);
  c = gg(c, d, a, b, blk[11], 14, 643717713);
  b = gg(b, c, d, a, blk[0], 20, -373897302);
  a = gg(a, b, c, d, blk[5], 5, -701558691);
  d = gg(d, a, b, c, blk[10], 9, 38016083);
  c = gg(c, d, a, b, blk[15], 14, -660478335);
  b = gg(b, c, d, a, blk[4], 20, -405537848);
  a = gg(a, b, c, d, blk[9], 5, 568446438);
  d = gg(d, a, b, c, blk[14], 9, -1019803690);
  c = gg(c, d, a, b, blk[3], 14, -187363961);
  b = gg(b, c, d, a, blk[8], 20, 1163531501);
  a = gg(a, b, c, d, blk[13], 5, -1444681467);
  d = gg(d, a, b, c, blk[2], 9, -51403784);
  c = gg(c, d, a, b, blk[7], 14, 1735328473);
  b = gg(b, c, d, a, blk[12], 20, -1926607734);

  a = hh(a, b, c, d, blk[5], 4, -378558);
  d = hh(d, a, b, c, blk[8], 11, -2022574463);
  c = hh(c, d, a, b, blk[11], 16, 1839030562);
  b = hh(b, c, d, a, blk[14], 23, -35309556);
  a = hh(a, b, c, d, blk[1], 4, -1530992060);
  d = hh(d, a, b, c, blk[4], 11, 1272893353);
  c = hh(c, d, a, b, blk[7], 16, -155497632);
  b = hh(b, c, d, a, blk[10], 23, -1094730640);
  a = hh(a, b, c, d, blk[13], 4, 681279174);
  d = hh(d, a, b, c, blk[0], 11, -358537222);
  c = hh(c, d, a, b, blk[3], 16, -722521979);
  b = hh(b, c, d, a, blk[6], 23, 76029189);
  a = hh(a, b, c, d, blk[9], 4, -640364487);
  d = hh(d, a, b, c, blk[12], 11, -421815835);
  c = hh(c, d, a, b, blk[15], 16, 530742520);
  b = hh(b, c, d, a, blk[2], 23, -995338651);

  a = ii(a, b, c, d, blk[0], 6, -198630844);
  d = ii(d, a, b, c, blk[7], 10, 1126891415);
  c = ii(c, d, a, b, blk[14], 15, -1416354905);
  b = ii(b, c, d, a, blk[5], 21, -57434055);
  a = ii(a, b, c, d, blk[12], 6, 1700485571);
  d = ii(d, a, b, c, blk[3], 10, -1894986606);
  c = ii(c, d, a, b, blk[10], 15, -1051523);
  b = ii(b, c, d, a, blk[1], 21, -2054922799);
  a = ii(a, b, c, d, blk[8], 6, 1873313359);
  d = ii(d, a, b, c, blk[15], 10, -30611744);
  c = ii(c, d, a, b, blk[6], 15, -1560198380);
  b = ii(b, c, d, a, blk[13], 21, 1309151649);
  a = ii(a, b, c, d, blk[4], 6, -145523070);
  d = ii(d, a, b, c, blk[11], 10, -1120210379);
  c = ii(c, d, a, b, blk[2], 15, 718787259);
  b = ii(b, c, d, a, blk[9], 21, -343485551);

  x[0] = add32(a, x[0]); x[1] = add32(b, x[1]);
  x[2] = add32(c, x[2]); x[3] = add32(d, x[3]);
}
function cmn(q, a, b, x, s, t) {
  a = add32(add32(a, q), add32(x, t));
  return add32((a << s) | (a >>> (32 - s)), b);
}
function ff(a, b, c, d, x, s, t) { return cmn((b & c) | (~b & d), a, b, x, s, t); }
function gg(a, b, c, d, x, s, t) { return cmn((b & d) | (c & ~d), a, b, x, s, t); }
function hh(a, b, c, d, x, s, t) { return cmn(b ^ c ^ d, a, b, x, s, t); }
function ii(a, b, c, d, x, s, t) { return cmn(c ^ (b | ~d), a, b, x, s, t); }
function add32(a, b) { return (a + b) & 0xffffffff; }
