# TackShot · 图钉截图

Windows 上的截图 / 标注 / 贴图工具，C++17 + Qt 6 实现，**默认完全离线**。
识别全部走云端接口：百度图片翻译（文字+译文+坐标+整图贴合）、SimpleTex（公式 → LaTeX）、视觉大模型兜底。

![识别结果](docs/screenshot-ocr.png)

## 功能

| 模块 | 说明 |
| --- | --- |
| 截图 | 全局热键（默认 Ctrl+Alt+A）、框选实时跟手、多屏混合 DPI |
| 标注 | 矩形、椭圆、箭头、直线、画笔（贝塞尔平滑）、荧光笔、马赛克（笔刷）、文字、序号 |
| 标注编辑 | 点选标注 → 拖动移动、8 点手柄缩放、Delete 删除 |
| 长截图 | 滚动拼接，支持横向与纵向，自动找重叠 |
| 录制 | MP4（H.264 + AAC）与 GIF；系统声 / 麦克风 / 混音，WASAPI 原生格式采集 |
| 识别 | 百度图片翻译（文字/译文/坐标/贴合图）+ SimpleTex（公式 LaTeX）+ 视觉大模型兜底 |
| 翻译 | OpenAI 兼容接口（DeepSeek / Gemini / 自建），分块 + 缓存 + 术语表 + 降级 |
| 译图 | 逐行翻译后把译文渲染回原图，再钉到屏幕上 |
| 贴图 | 无边框钉图窗，滚轮缩放、双击 1:1、悬停标题条（复制/保存/关闭） |
| 外观 | 深色 / 浅色 / 跟随系统 |

## 下载安装

到 Releases 页面下载 TackShotSetup.exe（约 183 MB，含 OCR 与公式模型）。

- 单文件安装器，装到 %LOCALAPPDATA%\Programs\TackShot，不需要管理员权限；
- 首次运行会弹 SmartScreen（未签名），点「更多信息 → 仍要运行」；
- 卸载：安装目录下的 Uninstall.exe，或「应用和功能」里找 TackShot。

## 系统要求

- Windows 10 1809+ / Windows 11，x64
- 无需安装 VC++ 运行库或 Qt（安装包已内置）
- 多显示器、混合 DPI 已支持（每屏独立覆盖层）

## 从源码构建

依赖（自行准备，不入库）：Qt 6.8.x (MinGW 13.1)、MinGW-w64 13.1、ONNX Runtime 1.31.1 C API、模型文件。

```powershell
powershell -File tools\build.ps1            # 编译主程序 -> build\TackShot.exe
powershell -File tools\build_setup.ps1      # 打包安装器 -> dist\TackShotSetup.exe
```

模型目录结构：

```
models/
  ch_PP-OCRv4_det_infer.onnx   # 文本检测
  ch_PP-OCRv4_rec_infer.onnx   # 文本识别
  ppocr_keys_v1.txt            # 6623 字字典
  formula/                     # 公式识别（可缺省，缺省时 LaTeX 页为空）
    encoder_model.onnx
    decoder_model.onnx
    tokenizer.json
```

也可以直接从 Releases 下载 models.zip 解压到 dist\TackShot\models\。

## 隐私

- 截图、标注、OCR、长截图、录制全部本地完成，不联网；
- 只有「翻译」「在线识别」会联网，且必须先填 API Key；首次使用会弹确认；
- Key 用 Windows DPAPI 加密存放在 %LOCALAPPDATA%\TackShot\secrets.dat，不落明文；
- 翻译缓存只存译文，不存原图。

## 已知限制

- 识别需要联网；百度需 APPID/密钥，SimpleTex 需 UAT，视觉模型需支持图片输入；
- 混合 DPI 且两块屏缩放不同时，覆盖层只覆盖鼠标所在的那块屏；
- 未做代码签名，SmartScreen 会提示。

## 目录

```
src/        主程序
setup/      Win32 安装器桩（自解压 + 快捷方式 + 卸载）
res/        图标、manifest、版本资源
tools/      构建脚本、模型下载、mock 服务器、自检脚本
docs/       验证记录与模型调研
```

## 致谢

PaddleOCR 的 PP-OCRv4 模型、pix2text 的公式识别模型、Qt、ONNX Runtime。
