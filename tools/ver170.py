import io

# 版本 1.7.0
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\common.h"
s = io.open(p, encoding="utf-8").read().replace('#define APP_VERSION "1.6.1"', '#define APP_VERSION "1.7.0"')
io.open(p, "w", encoding="utf-8").write(s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\res\app.rc"
s = io.open(p, encoding="utf-8").read()
s = s.replace("FILEVERSION 1,6,1,0", "FILEVERSION 1,7,0,0").replace("PRODUCTVERSION 1,6,1,0", "PRODUCTVERSION 1,7,0,0")
s = s.replace('"1.6.1.0"', '"1.7.0.0"')
io.open(p, "w", encoding="utf-8").write(s)

# README：识别部分改为云端
p = r"C:\Users\laiki\.dsh\workspace\tackshot\README.md"
s = io.open(p, encoding="utf-8").read()
s = s.replace("内置 PP-OCR 文字识别与本地公式识别（输出 LaTeX）；翻译和在线识别需要你自己填 API Key。",
              "识别全部走云端接口：百度图片翻译（文字+译文+坐标+整图贴合）、SimpleTex（公式 → LaTeX）、视觉大模型兜底。")
s = s.replace("| 识别 | 本地 PP-OCRv4 文字 + pix2text-mfr 公式（→ LaTeX）；可切换在线视觉大模型 |",
              "| 识别 | 百度图片翻译（文字/译文/坐标/贴合图）+ SimpleTex（公式 LaTeX）+ 视觉大模型兜底 |")
s = s.replace("| **本地公式模型** | pix2text-mfr-1.5（114MB） | 已删 |", "")
s = s.replace("- 公式识别是「整块选区直通模型」，纯文字图也会跑一次（约 +0.9s），可在设置里关闭；\n", "")
s = s.replace("- 在线识别需要支持图片输入的模型（Gemini / Qwen-VL 等），DeepSeek 文本模型不支持；",
              "- 识别需要联网；百度需 APPID/密钥，SimpleTex 需 UAT，视觉模型需支持图片输入；")
io.open(p, "w", encoding="utf-8").write(s)
print("version 1.7.0 + README updated")
