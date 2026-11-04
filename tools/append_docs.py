import io, os

p = r"C:\Users\laiki\.dsh\workspace\tackshot\docs\VERIFY.md"
s = io.open(p, encoding="utf-8").read()
s += """
## 6. 本地 OCR（v1.1）

命令：TackShot.exe --ocr-selftest build\\ocrtest

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
"""
io.open(p, "w", encoding="utf-8").write(s)
print("verify ok")

p2 = r"C:\Users\laiki\.dsh\workspace\re_test123\report.md"
if os.path.exists(p2):
    t = io.open(p2, encoding="utf-8").read()
    t += """
---

## 附录：更正（2026-11-02 晚）

第 3.5 节曾判断 4 个 .bin 模型“用 16 字节密钥 XOR 即可还原为 ONNX”。后续用
onnxruntime 1.31 实际加载时，4 个文件全部报 Protobuf parsing failed，
而同一目录里明文的 paragraph_recognition.onnx 可以正常加载。

结论修正：异或只是第一层（或只覆盖了部分区段），文件头与节点名可读具有误导性；
完整模型还需要额外变换。实际可用的 OCR 改用公开的 PP-OCRv4 模型。
"""
    io.open(p2, "w", encoding="utf-8").write(t)
    print("re report updated")
