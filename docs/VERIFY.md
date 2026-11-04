# TackShot 验证记录

环境：Windows 11 ｜ 2560×1440 @125%（逻辑 2048×1152）｜ 单屏 VX2479-2K-PRO
工具链：Qt 6.8.3 (MinGW 13.1) ｜ GCC 13.1.0 ｜ MSVC 不可用

## 1. 构建

    === moc === / === windres === / === compile ===
      ok annotate / capture / config / hisimport / hotkey / main
      ok overlay / pinwindow / settingsdialog
      ok moc_config / moc_hotkey / moc_overlay / moc_pinwindow / moc_settingsdialog
    === link === / === built ===
    TackShot.exe  209,408 bytes

    TackShotSetup.exe 35.96 MB（stub 89 KB + 载荷 37.6 MB）

## 2. 抓屏自检（真实桌面，DXGI）

命令：`dist\TackShot\TackShot.exe --selftest build\selftest.png`

    version=1.0.0
    qt=6.8.3
    capture=2560x1440
    virtualRect=0,0 2560x1440
    dxgiAvailable=true
    screens=1
      screen VX2479-2K-PRO geom=0,0 2048x1152 dpr=1.25
    saved=true

结论：DXGI 可用，抓到 **2560×1440 物理像素**；Qt 报告逻辑分辨率 2048×1152（DPR 1.25），
说明 DPI 换算链路正确。

## 3. 界面 / 标注渲染自检（合成底图，不接触真实桌面）

命令：`TackShot.exe --overlay-demo build\overlay_demo.png`

    overlay=2000x1250
    saved=true

`2000×1250 = 1600×1000 × 1.25`，覆盖层按 DPR 正确栅格化。
快照见 `docs/screenshot-overlay.png`：选区 + 8 手柄 + 尺寸标签 + 9 个工具 + 颜色/线宽 +
撤销/重做/复制/保存/贴图/关闭 + 九类标注（矩形/椭圆/箭头/画笔/高亮/马赛克/文字/序号）。

导出链路：`TackShot.exe --overlay-demo build\final.png --final`

    final=1240x720
    saved=true

快照见 `docs/screenshot-final.png`：不带 UI 的成品图，尺寸等于选区。

## 4. 安装 / 卸载

    install exit=0
    --- installed ---
    files=23 MB=71.86
    D3Dcompiler_47.dll Qt6*.dll libgcc/libstdc++/libwinpthread
    TackShot.exe  TackShot.lnk  Uninstall.exe  platforms/ styles/ imageformats/ ...

    --- run installed app selftest ---
    app exit=0
    capture=2560x1440 ... saved=true

    before uninstall: 12 files
    uninstall exit=0
    removed

结论：单文件安装器能正确解包（21 个载荷文件）、建快捷方式、写卸载项；
安装后的程序可独立运行并抓屏；卸载能清空目录。

## 5. 兼容性

- PixPin 配置：读取 `PixPinConfig.json` 的 `{Key:{t,v}}` 并映射笔宽/颜色/圆角。
- PixPin 历史：`.his` = 元数据 + 内嵌 PNG + 尾部元数据；已实现按 PNG 签名与 IEND CRC
  边界提取，无需解析完整 Qt 序列化结构。

## 6. 本地 OCR（v1.1）

命令：TackShot.exe --ocr-selftest build\ocrtest

    init=ok
    elapsedMs=851
    lines=4
    [46,51 410x30]   score=0.994  TackShot本地文字识别
    [44,137 412x23]  score=0.955  He1oOCR12345ABCDEFG
    [43,217 493x26]  score=0.988  中文与English混排，标点：。，！？
    [40,288 481x23]  score=0.998  订单号SN-2026-0042金额128.50

- 输入是程序自己渲染的 1000x360 测试图（不涉及真实屏幕）；
- 4 行全部检出，坐标/置信度合理，耗时 < 1 秒；
- 已知问题：英文 Hello 被读成 He1o、单词间空格丢失（PP-OCR 的 CTC 固有倾向）。

## 7. 安装包（含 OCR 运行时）

    安装器 68.14 MB  ->  install exit=0
    files=32  MB=136.2   models=3   onnxruntime.dll=True
    安装后运行 --ocr-selftest：init=ok，4 行识别结果与开发目录一致

## 8. 关于 PixPin 自带模型的更正

早前判断“4 个 .bin 用 16 字节密钥异或即可还原为 ONNX”不成立：
异或后文件头与节点名可读，但完整文件无法通过 protobuf 解析（onnxruntime 报
Protobuf parsing failed），说明还存在一层未知变换。本次 OCR 因此改用
公开的 PP-OCRv4 模型（det + rec + 词典），与 PixPin 的实现无关。

## 9. 长截图拼接

命令：TackShot.exe --longshot-selftest build\lstest

    frames=3 matched=2
    canvas=600x1600 source=600x1800
    meanAbsDiff=0

合成源图 600x1800，按 500px 步长切成 600 高的帧（重叠 100px）。
拼接结果 600x1600 与源图对应区域逐像素一致（meanAbsDiff = 0），
说明重叠检测与追加行数计算正确，没有重复或缺失条带。

## 10. GIF 录制

命令：TackShot.exe --gif-selftest build\giftest.gif

    ok=true frames=24 bytes=34246
    独立解析器校验：size=320x180 frames=24 delays=[8,8,8,8] gct=True trailing=True

24 帧 320x180、每帧 80ms、带全局调色板、结尾 0x3B 正确。

## 11. 撤销 / 重做

命令：TackShot.exe --undo-selftest build\undo.txt

    counts=3,2,1,2

连续加 3 个标注 → 撤销两次剩 1 个 → 重做一次回到 2 个，栈行为符合预期。

## 12. 最终安装包

    安装器 68.22 MB  ->  install=0  files=32  MB=68.1
    安装后跑 --undo-selftest / --longshot-selftest / --gif-selftest 均通过

## 13. MP4 录制

命令：TackShot.exe --record-selftest build\rectest4.mp4 3

    ok=true frames=39 avgCapMs=6.92 avgEncMs=0 bytes=121124
    top boxes: ftyp / uuid / mdat / moov
    timescale=15000 duration=46099 -> 3.07s
    codec=avc1  640x360   samples=46

- 录 3 秒得到 3.07 秒时长，时间戳按真实时钟走；
- 独立的 box 解析器确认：ftyp + mdat + moov、avc1 视频轨、640x360、样本数一致；
- 采集走 GDI BitBlt，平均 7ms/帧；编码异步，不阻塞采集；
- 装到临时目录后再跑一遍：ok=true duration=2.07s (2 秒)，说明发布包里的运行时完整。

## 14. 录制音频（WASAPI）

命令：TackShot.exe --audio-selftest build\audiotest.mp4 3
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

## 23. 安装失败排查（err=32 文件占用）

用户报“安装失败”，日志定位：

    create failed err=32 target=...\Qt6Core.dll
    extract finished ok=31 failed=10

err=32 = ERROR_SHARING_VIOLATION —— TackShot 正在运行，安装器无法覆盖被加载的 DLL。

修复：
- 安装前检测安装目录下运行的 TackShot.exe，GUI 弹窗询问是否关闭，静默模式直接关闭；
- 写文件遇到 ERROR_SHARING_VIOLATION 时重试 8 次（间隔 300ms），覆盖“刚被杀进程尚未释放”的窗口；
- 失败对话框列出具体文件名与错误码。

验证：

    running instances = 1
    silent: terminated 1 running instance(s)
    extract finished ok=31 failed=0
    installer exit = 0
    instances after = 0

## 24. 识别 / 翻译能力升级（本地公式模型 + 在线视觉 + 新弹窗）

### 本地公式模型（pix2text-mfr-1.5，TrOCR 编码器-解码器）
- 模型：encoder 83.46MB + decoder 30.54MB + BPE tokenizer（1868 词表），MIT
- 预处理：缩放到 384x384，(x/255-0.5)/0.5
- 解码：贪心，<s>=1 起始、</s>=2 结束，上限 200 token
- 实测（C++ 实现 vs Python 参考，同一张图）：
    Python: \mathrm { x 2 + y 2 = r 2 }
    C++:    \mathrm{ x 2 + y 2 = r 2}    （仅空白规整差异）
    耗时：1039 ms（首次加载含初始化）/ 1068 ms（安装目录内）

### 在线视觉识别（VisionClient，OpenAI 兼容）
- mock 自检：normal / 401 不重试 / 403 不重试，ALL_PASS=true
- stats 返回 requests=3、lastHasImage=true，证明图片以 data URL 发出
- 错误分类：401/403 Key 无效、402 余额、429 重试、5xx 重试、超时、404 地址错

### 识别结果弹窗（OcrDialog）
- 左原图（识别框高亮、选中行橙色）+ 右「文字 / 译文 / LaTeX」三页
- 底部：源语言 -> 目标语言、模型下拉、翻译 / 译图 / 复制
- 顶栏徽标：后端、行数、耗时；离屏渲染截图 build/ocrdlg.png

### 翻译源语言
- 新增 translateSource（默认 English），prompt 改为把英文翻译成中文
- 缓存键加入源语言，改源语言不会命中旧缓存

### 安装包
- 183.08 MB（新增 114MB 公式模型），安装后 38 个文件、models 9 个
- 安装目录内跑 --formula-selftest：ready=true，latex 正确
