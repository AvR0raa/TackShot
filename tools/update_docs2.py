import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\README.md"
s = io.open(p, encoding="utf-8").read()

# 1) 功能表补充
anchor = "| **本地 OCR** | PP-OCRv4 det + rec（ONNX Runtime），DB 连通域检测 + CTC 解码，中英文数字混排 | ✅ |"
add = anchor + "\n" + "\n".join([
 "| **长截图** | 定时抓取 + 底部模板匹配自动拼接（灰度 / 亮度归一化 SAD 搜索） | ✅ |",
 "| **GIF 录制** | 10fps 抓屏 → 中位切分调色板 + 自研 LZW 编码器，无外部依赖 | ✅ |",
 "| **撤销/重做** | 标注快照栈，最多 60 步，Ctrl+Z / Ctrl+Shift+Z | ✅ |",
])
if anchor in s:
    s = s.replace(anchor, add, 1)
else:
    print("anchor missing")

# 2) 未实现表：去掉已完成项
for line in [
  "| 长截图 | 需要滚动捕获 + 帧间拼接 |\n",
  "| 录屏 / 动图 | 需要 ffmpeg 管道与音频采集 |\n",
  "| 长截图 | 需要滚动捕获 + 帧间拼接 |\r\n",
]:
    s = s.replace(line, "")
s = s.replace("| 录屏 / 动图 | 需要 ffmpeg 管道与音频采集 |", "| 视频录制（MP4/H.264） | 需要 ffmpeg 管道与 WASAPI 音频采集 |")

# 3) 新增小节
if "## 3. 架构" in s:
    s = s.replace("## 3. 架构", """## 2.2 长截图

- 选区后点「长图」，浮出一个小工具条，滚动目标窗口即可自动追加；
- 算法：每次抓取把画布底部一段缩放成 240px 宽的灰度模板，在被抓帧里做粗采样 SAD 搜索，
  取最优偏移换算重叠行数，只追加新增行；不匹配（页面没动）则跳过；
- 实测：3 帧重叠 100px 的合成长图，拼接结果与源图逐像素一致（meanAbsDiff = 0）。

## 2.3 GIF 录制

- 选区后点「录制」，10fps 抓屏，停止时生成 GIF；
- 编码器自研：5-5-5 直方图中位切分生成全局调色板（256 色）+ 标准 GIF LZW，
  不依赖 ffmpeg；文件结构已用独立解析器校验（帧数/延时/调色板/结尾字节）。

## 3. 架构""", 1)

# 4) 目录结构
s = s.replace("      ocr.cpp       PP-OCRv4 本地推理（det 连通域 + rec CTC）",
              "      ocr.cpp       PP-OCRv4 本地推理（det 连通域 + rec CTC）\n"
              "      longshot.cpp  长截图拼接（模板匹配）\n"
              "      gifenc.cpp    GIF 编码器（中位切分 + LZW）\n"
              "      sessions.cpp  长截图 / 录制 的浮窗与会话")

# 5) 限制
s = s.replace("- 撤销/重做只保留最近一步（单步）。", "- 长截图只支持竖向滚动；横向或带固定表头的页面需要额外处理。")
io.open(p, "w", encoding="utf-8").write(s)
print("readme ok", len(s))

# 6) VERIFY 追加
p2 = r"C:\Users\laiki\.dsh\workspace\tackshot\docs\VERIFY.md"
v = io.open(p2, encoding="utf-8").read()
v += """
## 9. 长截图拼接

命令：TackShot.exe --longshot-selftest build\\lstest

    frames=3 matched=2
    canvas=600x1600 source=600x1800
    meanAbsDiff=0

合成源图 600x1800，按 500px 步长切成 600 高的帧（重叠 100px）。
拼接结果 600x1600 与源图对应区域逐像素一致（meanAbsDiff = 0），
说明重叠检测与追加行数计算正确，没有重复或缺失条带。

## 10. GIF 录制

命令：TackShot.exe --gif-selftest build\\giftest.gif

    ok=true frames=24 bytes=34246
    独立解析器校验：size=320x180 frames=24 delays=[8,8,8,8] gct=True trailing=True

24 帧 320x180、每帧 80ms、带全局调色板、结尾 0x3B 正确。
"""
io.open(p2, "w", encoding="utf-8").write(v)
print("verify ok")
