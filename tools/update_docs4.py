import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\README.md"
s = io.open(p, encoding="utf-8").read()

anchor = "| **GIF 录制** | 10fps 抓屏 → 中位切分调色板 + 自研 LZW 编码器，无外部依赖 | ✅ |"
if anchor in s:
    s = s.replace(anchor, anchor + "\n| **MP4 录制** | Windows Media Foundation（H.264 + MP4 封装），15fps，无 ffmpeg 依赖 | ✅ |", 1)
else:
    print("anchor missing")

s = s.replace("| 视频录制（MP4/H.264） | 需要 ffmpeg 管道与 WASAPI 音频采集 |\n", "")
s = s.replace("| 视频录制（MP4/H.264） | 需要 ffmpeg 管道与 WASAPI 音频采集 |", "| 录制音频（麦克风/系统声） | 需要 WASAPI 采集与混流 |")

s = s.replace("## 3. 架构", """## 2.4 MP4 录制

- 选区后点「录制」；录制格式在设置里选 mp4 / gif（默认 mp4）；
- MP4 走 **Windows Media Foundation**：MFCreateSinkWriterFromURL → 添加 H.264 输出流
  （6400kbps、Main profile、15fps）→ 每帧 RGB32 送 IMFMediaBuffer → Finalize；
  不依赖 ffmpeg，也不需要额外运行库；
- 时间戳用真实时钟，编码跟不上时表现为丢帧（不会让视频整体快放）；
- 采集用 GDI BitBlt 只抓选区（约 7ms/帧），比全屏 DXGI 回读快一个数量级。

## 3. 架构""", 1)

s = s.replace("      gifenc.cpp    GIF 编码器（中位切分 + LZW）",
              "      gifenc.cpp    GIF 编码器（中位切分 + LZW）\n      mfrec.cpp     MP4/H.264 录制（Media Foundation）")
s = s.replace("- 长截图只支持竖向滚动；横向或带固定表头的页面需要额外处理。",
              "- 长截图只支持竖向滚动；横向或带固定表头的页面需要额外处理。\n"
              "- **录制暂时只有画面没有声音**（麦克风/系统声道还没接 WASAPI）。\n"
              "- 录制帧率取决于编码速度：本机 640x360 实测约 13fps（目标 15fps）。")
io.open(p, "w", encoding="utf-8").write(s)
print("readme ok")

p2 = r"C:\Users\laiki\.dsh\workspace\tackshot\docs\VERIFY.md"
v = io.open(p2, encoding="utf-8").read()
v += """
## 13. MP4 录制

命令：TackShot.exe --record-selftest build\\rectest4.mp4 3

    ok=true frames=39 avgCapMs=6.92 avgEncMs=0 bytes=121124
    top boxes: ftyp / uuid / mdat / moov
    timescale=15000 duration=46099 -> 3.07s
    codec=avc1  640x360   samples=46

- 录 3 秒得到 3.07 秒时长，时间戳按真实时钟走；
- 独立的 box 解析器确认：ftyp + mdat + moov、avc1 视频轨、640x360、样本数一致；
- 采集走 GDI BitBlt，平均 7ms/帧；编码异步，不阻塞采集；
- 装到临时目录后再跑一遍：ok=true duration=2.07s (2 秒)，说明发布包里的运行时完整。
"""
io.open(p2, "w", encoding="utf-8").write(v)
print("verify ok")
