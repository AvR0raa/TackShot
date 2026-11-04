import io

p = r"C:\Users\laiki\.dsh\workspace\tackshot\README.md"
s = io.open(p, encoding="utf-8").read()

s = s.replace("| **长截图** | 定时抓取 + 底部模板匹配自动拼接（灰度 / 亮度归一化 SAD 搜索） | ✅ |",
              "| **长截图** | 定时抓取 + 模板匹配自动拼接，竖向/横向自动判别 | ✅ |")
s = s.replace("| **MP4 录制** | Windows Media Foundation（H.264 + MP4 封装），15fps，无 ffmpeg 依赖 | ✅ |",
              "| **MP4 录制** | Windows Media Foundation（H.264 + AAC + MP4 封装），15fps，无 ffmpeg 依赖 | ✅ |\n"
              "| **录制音频** | WASAPI：系统回环 / 麦克风 / 两者混音 | ✅ |")
s = s.replace("| 录制音频（麦克风/系统声） | 需要 WASAPI 采集与混流 |\n", "")

s = s.replace("""- 算法：每次抓取把画布底部一段缩放成 240px 宽的灰度模板，在被抓帧里做粗采样 SAD 搜索，
  取最优偏移换算重叠行数，只追加新增行；不匹配（页面没动）则跳过；
- 实测：3 帧重叠 100px 的合成长图，拼接结果与源图逐像素一致（meanAbsDiff = 0）。""",
"""- 算法：每次抓取把画布底部（竖向）或右侧（横向，内部转置复用同一套逻辑）一段缩放成 240px
  灰度模板，在被抓帧里做粗采样 SAD 搜索，取最优偏移换算重叠行数/列数，只追加新增部分；
- 两个方向都试一次，取匹配成立且新增面积更小的那个；
- 实测：竖向 600x1800、横向 1800x600 两组合成图，拼接结果与源图逐像素一致（meanAbsDiff = 0）。""")

s = s.replace("""- 时间戳用真实时钟，编码跟不上时表现为丢帧（不会让视频整体快放）；
- 采集用 GDI BitBlt 只抓选区（约 7ms/帧），比全屏 DXGI 回读快一个数量级。""",
"""- 时间戳用真实时钟，编码跟不上时表现为丢帧（不会让视频整体快放）；
- 采集用 GDI BitBlt 只抓选区（约 7ms/帧），比全屏 DXGI 回读快一个数量级；
- 音频：WASAPI 采集 48kHz/16bit/立体声，LOOPBACK 标志抓系统声，麦克风走默认录音设备；
  两者都开时逐样本相加并限幅；PCM 直接作为 AAC 流送入同一个 SinkWriter，与视频共用时间轴。
  设置里可选 none / system / mic / both。""")

s = s.replace("- 录制暂时只有画面没有声音（麦克风/系统声道还没接 WASAPI）。\n", "")
s = s.replace("- 检测框按轴对齐矩形处理，斜排文字（旋转/透视）会退化。",
              "- 检测框按轴对齐矩形处理，斜排文字（旋转/透视）会退化。\n"
              "- 混合 DPI：各屏缩放不同时，覆盖层只覆盖光标所在的那块屏（不支持跨屏框选），"
              "这样每块屏的坐标换算才是精确的。")
s = s.replace("      mfrec.cpp     MP4/H.264 录制（Media Foundation）",
              "      mfrec.cpp     MP4/H.264+AAC 录制（Media Foundation）\n"
              "      audiocap.cpp  WASAPI 采集（系统回环 / 麦克风）")
io.open(p, "w", encoding="utf-8").write(s)
print("readme ok")

p2 = r"C:\Users\laiki\.dsh\workspace\tackshot\docs\VERIFY.md"
v = io.open(p2, encoding="utf-8").read()
v += """
## 14. 录制音频（WASAPI）

命令：TackShot.exe --audio-selftest build\\audiotest.mp4 3
（自检先播放 1kHz 正弦音，再用系统回环采集）

    open=true capture=true
    frames=37 audioBytes=562560
    rms=8462.66 peak=12001
    MP4: trak1=avc1 640x360 samples=45 / trak2=mp4a 48000Hz samples=138
    duration=3.23s

- 采集 562,560 字节 = 2.93s @48k/16bit/立体声，与录制时长吻合；
- RMS 8463、峰值 12001，与注入的 12000 幅度正弦波一致（理论 RMS 8485），
  证明回环采集到的是真实音频而不是静音；
- MP4 同时含 avc1 视频轨与 mp4a 音频轨。

## 15. 横向长截图

    frames=3 matched=2 dir=1
    canvas=1600x600 source=1800x600
    meanAbsDiff=0

1800x600 宽图按 500px 步长切帧（重叠 100px），自动判别为横向（dir=1），
拼回结果与源图逐像素一致；竖向用例（600x1800）同样 meanAbsDiff=0。

## 16. 混合 DPI（真机，两块屏）

本机实际就是混合 DPI：主屏 2048x1152@125%（物理 2560x1440），副屏 2560x1440@100%。

    screens=2 capture=5120x1440 virt=0,0
    screen VX2479-2K-PRO  logical=2048x1152 dpr=1.25 physical=2560x1440
      overlayLogical=2048x1152 scale=1.25 mapRatio=1.25 widthError=0 pass=true
    screen NE156QHM-NY1  logical=2560x1440 dpr=1 physical=2560x1440
      overlayLogical=2560x1440 scale=1 mapRatio=1 widthError=0 pass=true
    ALL_PASS=true

另外用 QT_SCALE_FACTOR 模拟 150% / 200% 也全部通过（mapRatio 与 dpr 一致，宽度误差 <= 0.5px）。
实现上：各屏缩放不同时，覆盖层只覆盖光标所在屏，避免“整屏按主屏 dpr 缩放”导致副屏错位。
"""
io.open(p2, "w", encoding="utf-8").write(v)
print("verify ok")
