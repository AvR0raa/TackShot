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

## 25. 1.8.0：翻译改百度通用文本翻译（与识别共用凭据）

### 实现
- `BaiduTextTranslate`（baidu.cpp）：`/api/trans/vip/translate`，sign=md5(appid+q+salt+密钥)，
  表单 POST；54003/52001/52002 自动等待 1.1s 重试（标准版 QPS=1），最多 3 次；
  错误码映射中文提示；`TACKSHOT_BAIDU_TEXT_ENDPOINT` 可覆盖端点（自检用）
- `TranslateClient::doRequest` 按 `p.id=="baidu"` 分发：appId 取 Config、密钥取
  DPAPI `baidu_secret`（即「识别」页凭据），语言名 -> 语言码复用 `baiduLangCode`
  （自 overlay.cpp 的 toBaiduLang 移出共享）
- 引擎预设新增 `baidu` 并设为默认；1.7 存量配置若 provider=deepseek 且已配置
  百度凭据，load() 时自动迁移到 baidu
- 识别结果弹窗：配置了百度凭据即视为在线可用（原来必须填 OpenAI Key，
  导致只配百度时「翻译/译图」按钮一直灰）；buildChain 支持 baidu 条目
- 设置 → 翻译：引擎选百度时 Base URL/模型/API Key 三行禁用并清空，
  Key 占位符提示「复用『识别』页的百度密钥」；测试连接走百度密钥

### 自检（mock_translate_server.py 新增 /baidu 路由：表单签名校验、54003、54001）
命令：`TackShot.exe --baidu-text-selftest http://127.0.0.1:8899/baidu build\baidu_text_report.txt`

    normal: ok=1 lines=2 text=【中】Hello, world… pass=1     （多行逐行返回）
    badSign: ok=0 code=54001 err=…（签名错误…） pass=1
    limit54003: ok=1 pass=1                                    （限流重试成功）
    dispatch: ok=1 provider=baidu pass=1                       （TranslateClient 分发+语言码映射）
    unconfigured: ok=0 err=百度翻译未配置 APPID/密钥 pass=1
    ALL_PASS=true

OpenAI 路径回归 `--translate-selftest`：7/7 ALL_PASS=true（未受影响）。
UI：--ui-preview 翻译页截图确认三框禁用、无 baidu-text 残留。

### 注意
- 需在百度翻译开放平台分别开通「通用文本翻译」与「图片翻译」（同一 APPID/密钥）；
- 术语表只对大模型引擎生效（百度 MT 不支持注入术语）。

## 26. 1.8.0 补丁：翻译批量提速 + 译图 52003 定位

### 翻译慢的根因与修复
- 原因：识别结果弹窗里「翻译/译图」逐行发请求（每行 1 次 HTTP），百度标准版 QPS=1，
  N 行 ≥N 秒且易触发 54003 重试等待
- 修复：`TranslateClient::translateBatch`——百度引擎把全部行以 \n 合并成一次请求
  （trans_result 按行返回），超 5000 字节自动分批、批间限速 1.1s；OpenAI 引擎仍逐行；
  主引擎失败行由备用引擎补齐
- 自检 case6：3 行批量 -> mock 请求数 +1（一次请求），pass

### 译图无法使用的定位（--baidu-live-check 真实 API 诊断）
    appId=2025REDACTED0009 secret=(present) paste=1
    text: ok=1 out=你好，世界                     （通用文本翻译正常）
    picture: ok=0 code=52003 UNAUTHORIZED USER    （图片翻译服务未开通）

结论：APPID 只开通了「通用文本翻译」，未开通「图片翻译」（开放平台两个独立开关）。
识别失败弹窗已加 52003 引导文案。

### 备注
- live-check 在受限环境跑时 %LOCALAPPDATA% 被重定向到 LocalLow 会读到空配置，
  需 TACKSHOT_DATA_DIR 指向真实数据目录；GUI 不受影响

## 27. 1.8.1：图片翻译 52003 真正根因——setQuery 缺失（更正 §26 结论）

### 更正
§26 判定的「图片翻译服务未开通」是**误判**。用户控制台已开通；真实根因是客户端 bug。

### 根因
`baidu.cpp` BaiduPictureTranslate：QUrlQuery 构建了全部鉴权参数（appid/sign/salt/cuid/mac/
version/paste）但**从未 url.setQuery(q) 挂回 URL**，参数全部丢弃，百度收到无 appid 的裸请求
-> 52003 UNAUTHORIZED USER。该 bug 自 1.7.0 引入；旧 mock 的 picture 路由不校验参数，
返回固定成功响应，所以 --cloud-selftest 一直"全过"。

### 定位过程
- tools/baidu_probe.py（DPAPI 解密凭据 + 直发真实 API）：参数放 query 的请求返回
  69004（鉴权通过、识别为空，测试图无文字）——证明服务与签名公式没问题
- 同凭据 app 内请求返回 52003 —— 对比出"参数没发出去"

### 修复与防回归
- baidu.cpp:75 补 `url.setQuery(q)`
- mock_cloud_server.py picture 路由加严格校验：query 缺 appid -> 52003；
  sign != md5(appid+md5(png)+salt+cuid+mac+secret-test) -> 54001；提取 PNG 算真实签名
- 反向验证：注释 setQuery 重编译 -> --cloud-selftest exit=24（baidu pass=0，mock 拦住）；
  恢复 -> ALL_PASS=true

### 真实 API 验证（--baidu-live-check，用户真实凭据）
    text: ok=1 out=你好，世界
    picture: ok=1 code=0 lines=1 pasteImg=1
      line: Hello -> 你好

## 28. 1.9.0：L2 云代理托管——密钥只存云端，安装包只有代理 URL

### 架构
- cloud/worker.js（Cloudflare Workers）与 cloud/scf_main.py（腾讯云函数）等价实现：
  /picture /text /simpletex 三路由，接收客户端业务参数，云端补 appid/salt/sign（或 token）
- 客户端 src/managed.cpp：内置代理 URL 由 build.ps1 从 tools/proxy_local.json 生成
  src/proxy_embedded.inc（gitignore）；环境变量 TACKSHOT_MANAGED_PROXY 可覆盖
- 优先级：用户自配凭据（设置→识别）> 内置云代理；凭据空且无代理 -> 明确报错
- 托管请求只含 from/to/paste 或 q/from/to，**不含任何签名/凭据字段**

### 自检 --proxy-selftest（mock_proxy_server.py:8903 + mock_cloud_server.py:8902）
    picture: ok=1 lines=2 paste=60x30 credsLeaked=0 pass=1
    text:    ok=1 lines=2 credsLeaked=0 pass=1
    batch:   failed=0 lines=3 requests=1 credsLeaked=0 pass=1
    simpletex: ok=1 latex=E = m c^{2} credsLeaked=0 pass=1
    priority: ok=1 lines=2 proxyUntouched=1 pass=1   （有凭据时直连，代理零请求）
    ALL_PASS=true

credsLeaked=0 由 mock 断言（请求里出现 appid/sign/salt/token 头任一即置位）。

### 回归
--cloud-selftest / --translate-selftest / --baidu-text-selftest / --ui-preview 全部
ALL_PASS（托管不影响直连与 OpenAI 路径）。worker.js 内嵌 MD5 对拍 node crypto：
空串/中文/200 字符/63-65 边界长度全 OK。

### 发布安全
- GitHub 源码：proxy_embedded.inc 为空模板（.gitignore 排除生成版本），无 URL 无密钥
- 全历史扫描无凭据（唯一命中为 manifest 模板 publicKeyToken）
- docs/VERIFY.md 中历史调试 APPID 已脱敏

## 29. 1.9.0 补充：腾讯云函数 URL 实测三坑与 JSON 协议终局

### 踩坑记录（腾讯云 SCF + 函数 URL，均与文档不符，以实测为准）
1. 环境变量注入进程 os.environ（不在 context 对象上）
2. event.queryString 是解析好的 dict（不是文档写法的原始字符串）
3. 二进制 multipart body 被网关按 UTF-8 强行解码，无效字节替换为 U+FFFD，
   图片有损不可恢复（dbg 字段实测：bodyLen 749 << 实际体积）

### 终局协议：图片走 JSON + base64
客户端托管模式发 {"image": "<base64>"} + query 参数；云端（scf_main.py extract_image /
worker.js readImageBytes）解码后构造 multipart 转发百度。text 路由不受影响（纯表单）。

### 真实代理验证（--baidu-live-check，腾讯云广州 + 用户真实凭据云端签名）
    text:    ok=1 out=你好，世界
    picture: ok=1 code=0 lines=1 pasteImg=1  (Hello -> 你好)
    simpletex: ok=1 latex=\mathrm{HELO}      （合成字模图）
    托管模式（空凭据走内置代理）：text/picture 均 ok=1

### 客户端自检
--proxy-selftest 5/5（credsLeaked=0，JSON 协议）；--cloud-selftest 直连回归通过；
本地 SCF 事件级测试 tools/test_scf_local.py 8/8（含 queryString-dict、JSON、latin1 兜底）。

## 30. 1.9.0 补充：识图提速（并行 + 智能压缩）

### 慢因
1. 串行链路：SimpleTex 公式识别与百度图片翻译先后各等一次网络往返（各 1~3s）
2. 截图固定 PNG 无损：真实屏幕截图常 1~2MB，云代理链路再 +33% base64 膨胀

### 优化
- overlay onOcr：公式/百度两条云端调用 QThreadPool 并行，总耗时=max(两者)；
  主线程轮询 processEvents 保持响应（90s 兜底）
- encodeImageForUpload（baidu.h 导出）：≤300KB 用 PNG 无损；大图 JPG q85→70→55
  递降，仍超限按 0.75 缩放重试。托管上限 2.5MB / 直连 3.9MB；SimpleTex 沿用
  （2048 长边 + 2MB 上限）。multipart Content-Type/文件名按魔数自适应
- 自检适配：内置托管可用后「空凭据=报错」语义过时——cloud/baidu-text 自检开头
  TACKSHOT_MANAGED_PROXY=off 强制直连语义；managed 支持 "off" 显式禁用值

### 实测（live-check，400x120 合成小图）
    直连 picture 922ms / 托管 picture 1292ms（代理一跳 +370ms；服务端固有 ~900ms）
    --proxy-selftest 5/5、--cloud-selftest、--baidu-text-selftest、--translate-selftest
    回归全过；mock 支持 JPG 魔数

## 31. 1.9.0 补充：安装器 UI 更新

- 标题：硬编码 1.0.0 -> 动态引用 src/common.h 的 APP_VERSION（WIDEN 宏转宽字符，
  以后 bump 版本安装器自动同步）
- 副标题：「本地截图/标注/贴图工具（无网络依赖）」（1.0 时代文案）->
  「截图 / 标注 / 贴图 / 录屏，云识别翻译开箱即用」
- 新增灰色小字提示行（WM_CTLCOLORSTATIC 上色）：「识图/翻译走云端（密钥云端保管）·
  热键 Ctrl+Alt+A」；按钮下移、窗口 478x240 -> 478x258
- 图标修复：app.rc 的 IDI_ICON1（字符串符号）改数字 ID 1，安装器窗口/任务栏现在
  正确显示 TackShot 图标
- manifest assemblyIdentity 版本 1.0.0.0 -> 1.9.0.0
- 布局校验：副标题/小字按 -16/-13 字宽计算均 <430px 控件宽，无截断；
  PrintWindow 首轮截图确认标题、版本号、图标正常

## 32. 1.9.0 补充：识别/译图功能拆分 + 安装器精简

### 拆分（用户需求：识别太慢、两功能分开）
- 旧流程：识别 = SimpleTex 公式 + 百度图片翻译(带贴合渲染) 全都跑，即使图里没公式
  也要多一路上传识别；贴合渲染（paste=1）在百度服务端拖慢响应
- 新流程：
  · 识别（快）：只调百度图片翻译，paste=0 不渲染贴合图 -> 只要文字/坐标/译文
  · 公式：懒加载——结果窗口切到 LaTeX 页签才调 SimpleTex（latexRequested 信号，
    OcrDialog m_latexAsked 一次性）
  · 译图（独立）：点「译图」才按设置里的贴合方式再调一次百度，钉整图贴合结果；
    失败降级为坐标本地回填
- 设置页「贴合」改名「译图贴合」，文案注明仅译图时生效
- overlay 的 QThreadPool 并行框架随单路化移除（回简单同步结构）

### 安装器精简（用户需求：删无关信息）
- 删副标题与灰色小字提示行，仅保留：标题+版本 / 安装位置 / 进度 / 状态 / 安装取消
- 窗口 478x258 -> 478x236；动态版本号与图标修复保留（§31）

### 回归
--proxy-selftest 5/5、--cloud-selftest、--baidu-text-selftest、--translate-selftest、
--ocr-dialog-preview 全部通过
