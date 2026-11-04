import io

p = r"C:\Users\laiki\.dsh\workspace\tackshot\README.md"
s = io.open(p, encoding="utf-8").read()

anchor = "| **录制音频** | WASAPI：系统回环 / 麦克风 / 两者混音 | ✅ |"
if anchor in s:
    s = s.replace(anchor, anchor + "\n| **AI 翻译** | OCR 文本 → DeepSeek（默认）/ Gemini / 自定义 OpenAI 兼容；DPAPI 存 Key | ✅ |", 1)

s = s.replace("## 3. 架构", """## 2.5 AI 翻译

- 入口：识别结果面板里的「翻译」按钮（OCR 文本 → 译文，可复制）；
- 客户端：TranslateClient，只依赖 Qt6Network，走 OpenAI 兼容的 /chat/completions，
  所以 DeepSeek / Gemini(OpenAI 兼容) / 自建 vLLM / Ollama / 中转站都能直接填；
- 预设：DeepSeek（默认，deepseek-flash）、Gemini（gemini-3.8-flash）、自定义；
- 请求：temperature=0.2、非流式、45s 超时；system prompt 要求"只输出译文、保留段落与编号、
  代码/URL/数字原样保留"；
- 错误处理：401/403 不重试，402 余额不足，429 与 5xx 退避重试（1s/2s，最多 3 次）；
- 隐私：首次翻译弹一次确认（发送字符数 + 目标域名），可记住；日志不记录正文；
- 密钥：CryptProtectData（DPAPI，用户级）写入 secrets.dat，配置里不落明文。

## 3. 架构""", 1)

s = s.replace("      audiocap.cpp  WASAPI 采集（系统回环 / 麦克风）",
              "      audiocap.cpp  WASAPI 采集（系统回环 / 麦克风）\n"
              "      translate.cpp OpenAI 兼容翻译客户端（DeepSeek / Gemini / 自定义）\n"
              "      secrets.cpp   DPAPI 加密的本地密钥存储")

s = s.replace("- 混合 DPI：各屏缩放不同时，覆盖层只覆盖光标所在的那块屏（不支持跨屏框选），这样每块屏的坐标换算才是精确的。",
              "- 混合 DPI：各屏缩放不同时，覆盖层只覆盖光标所在的那块屏（不支持跨屏框选），这样每块屏的坐标换算才是精确的。\n"
              "- 翻译是整段直翻，没有术语表/翻译记忆；长文未做分段。\n"
              "- 没有 API Key 时翻译按钮会提示去设置里填；离线环境不可用。")
io.open(p, "w", encoding="utf-8").write(s)
print("readme ok")

p2 = r"C:\Users\laiki\.dsh\workspace\tackshot\docs\VERIFY.md"
v = io.open(p2, encoding="utf-8").read()
v += """
## 17. AI 翻译客户端（mock 服务，无需真实 Key）

自建 mock（tools/mock_translate_server.py）模拟 OpenAI 兼容接口，三种路径：

    normal:   ok=1 attempts=1 text=你好，世界                     pass=1
    auth401:  ok=0 status=401 attempts=1 err=API Key 无效或无权限   pass=1
    retry429: ok=1 attempts=3 text=你好，世界                     pass=1
    ALL_PASS=true

- 正常请求：1 次成功，解析 choices[0].message.content；
- 401：识别为鉴权失败且不重试；
- 429：退避重试第 3 次成功，attempts 计数正确。

## 18. 密钥存储（DPAPI）

    saved=1 roundtrip=1 plaintextInFile=0 storeSize=389 pass=true

写入后用 CryptUnprotectData 读回与原值一致；文件里搜不到明文 key（存的是 base64 的 DPAPI 密文）。

说明：沙箱限制写 %APPDATA%，为此新增 TACKSHOT_DATA_DIR 环境变量做数据目录重定向
（同时也是便携模式开关），自检通过它把数据写到工作区。

## 19. 最终安装包

    安装器 68.31 MB  ->  install=0  files=32
    装完后在安装目录跑 --translate-selftest / --secret-selftest：全部 PASS
"""
io.open(p2, "w", encoding="utf-8").write(v)
print("verify ok")
