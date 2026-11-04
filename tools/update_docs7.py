import io

p = r"C:\Users\laiki\.dsh\workspace\tackshot\README.md"
s = io.open(p, encoding="utf-8").read()

s = s.replace("- 翻译是整段直翻，没有术语表/翻译记忆；长文未做分段。",
              "- 译图是覆盖式：在原文位置擦除后重绘，不重排整段，长句会被压缩字号或裁切。")

old_block = """- 隐私：首次翻译弹一次确认（发送字符数 + 目标域名），可记住；日志不记录正文；
- 密钥：CryptProtectData（DPAPI，用户级）写入 secrets.dat，配置里不落明文。"""
new_block = old_block + """

### 长文本、术语表、缓存、降级

- 分段：按段落切，单段超过 N 字（设置里可调，默认 1500）再按句号切；逐段翻译后按序拼回，
  某段失败只占位不中断；
- 术语表：设置里按 原文=译法 每行一条，会拼进 system prompt 强制遵守；
- 缓存：sha256(文本 + 模型 + 目标语言 + 术语表) 作为键，命中直接返回（jsonl 存储，4000 条上限）；
- 降级：主引擎失败（限流/余额/服务端错误）自动切备用引擎，两个引擎的 Key 各自独立保存。

### 译图

识别结果面板里的「译图」逐行翻译，然后按 OCR 框把译文渲染回原图（擦除原文区域、
按框宽自动缩字号、背景色从框外取样），结果直接作为贴图钉在屏幕上。"""
if old_block in s:
    s = s.replace(old_block, new_block, 1)
else:
    print("MISS block")
io.open(p, "w", encoding="utf-8").write(s)
print("readme ok")

p2 = r"C:\Users\laiki\.dsh\workspace\tackshot\docs\VERIFY.md"
v = io.open(p2, encoding="utf-8").read()
v += """
## 20. 翻译进阶能力（分块 / 缓存 / 术语表 / 降级）

同一套 mock 自检扩展到 7 项：

    normal:   ok=1 chunks=1 text=你好，世界                      pass=1
    auth401:  ok=0 chunkFailed=1 err=API Key 无效或无权限          pass=1
    retry429: ok=1 text=你好，世界                               pass=1
    chunk:    ok=1 chunks=3 requests=3                          pass=1
    cache:    ok=1 fromCache=1 newRequests=0                     pass=1
    glossary: ok=1 marker=GLOSSARY_OK|                           pass=1
    fallback: primaryOk=0 backupOk=1                             pass=1
    ALL_PASS=true

- 分块：40 段中文按 500 字切块，块数与实际请求数一致（3/3）；
- 缓存：同样内容第二次翻译不再发请求（newRequests=0）且返回一致；
- 术语表：mock 检测到 system prompt 里的术语表后回打标记，证明注入生效；
- 降级：主引擎 401 失败后备用引擎成功。

## 21. 译图（图片翻译回填）

    ocrInit=true  lines=3  translated=3  saved=true

流程：合成图 → 本地 OCR（3 行）→ 逐行翻译 → 按 OCR 框擦除原文并重绘译文 → 落盘。
渲染效果已人工查看：原文被完全覆盖，译文随框宽自动缩字号。

## 22. 发布包复核

    安装器 68.36 MB -> install=0 files=32
    安装目录内跑 --translate-selftest：ALL_PASS=true
    安装目录内跑 --translate-image-selftest：lines=3 translated=3 saved=true
"""
io.open(p2, "w", encoding="utf-8").write(v)
print("verify ok")
