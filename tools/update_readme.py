import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\README.md"
lines = io.open(p, encoding="utf-8").read().split("\n")
out = []
inserted_ocr_row = False
for ln in lines:
    if ln.startswith("| 本地 OCR | 需要接入"):
        continue
    out.append(ln)
    if (not inserted_ocr_row) and ln.startswith("| **PixPin 历史兼容**"):
        out.append("| **本地 OCR** | PP-OCRv4 det + rec（ONNX Runtime），DB 连通域检测 + CTC 解码，中英文数字混排 | ✅ |")
        inserted_ocr_row = True
    if ln.strip() == "## 3. 架构":
        idx = len(out) - 1
        section = [
            "## 2.1 本地 OCR",
            "",
            "- 模型：PP-OCRv4 det + rec（ONNX），词典 6623 字，全部离线；",
            "- 推理：onnxruntime 1.31（LoadLibrary + OrtGetApiBase，不依赖 import lib）；",
            "- 检测：长边限制 1280、均值/方差 0.5 归一化 → DB 概率图 → 阈值 0.3 + 2×2 膨胀 → 8 连通域 → 置信度过滤 → 按行排序；",
            "- 识别：高度归一到 48、宽度按比例（上限 1600）、CTC 解码（blank=0，重复折叠）；",
            "- 性能：1000×360 的图约 0.9 秒（4 行，纯 CPU）；",
            "- 入口：框选后点工具条「识别」，结果可编辑、一键复制。",
            "",
        ]
        out[idx:idx] = section

text = "\n".join(out)
text = text.replace("      capture.cpp   DXGI 桌面复制 + Qt 兜底，输出物理像素虚拟桌面",
                    "      capture.cpp   DXGI 桌面复制 + Qt 兜底，输出物理像素虚拟桌面\n      ocr.cpp       PP-OCRv4 本地推理（det 连通域 + rec CTC）")
text = text.replace("- 抓屏走 DXGI；被保护的窗口（DRM/独占全屏）会抓成黑块，此时自动降级到 GDI。",
                    "- 抓屏走 DXGI；被保护的窗口（DRM/独占全屏）会抓成黑块，此时自动降级到 GDI。\n"
                    "- OCR 对英文单词间空格还原较弱（CTC 本身倾向丢空格），中文准确率好于英文。\n"
                    "- 检测框按轴对齐矩形处理，斜排文字（旋转/透视）会退化。")
text = text.replace("（21 个文件 ≈ 72 MB）", "（32 个文件 ≈ 136 MB，含 onnxruntime 与 OCR 模型）")
io.open(p, "w", encoding="utf-8").write(text)
print("ok", len(text))
