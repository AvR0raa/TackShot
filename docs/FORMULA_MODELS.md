# 本地公式识别 + 文字识别升级：ONNX 选型报告

> 目标：在 TackShot 现有「PP-OCRv4 det(4.5MB) → DB 后处理 → rec(10.3MB)」管线上，补一条**离线公式识别**（图片 → LaTeX），并把**文字识别**升级到更强的移动端模型。
> 约束：只用 Qt6 + STL + Win32 + onnxruntime C API，不允许第三方依赖，模型体积尽量 ≤ 100MB，全离线。
> 本报告所有体积/耗时数据来自 2026-11-04 的实际下载与 onnxruntime 1.31 实测（本机 8 线程 CPU），标注「官方」的指标取自 PaddleOCR / HuggingFace 模型卡。

---

## 0. 结论速览

| 项目 | 结论 |
| --- | --- |
| 公式模型首选 | **pix2text-mfr-1.5**（breezedeus，TrOCR 架构，MIT，官方 ONNX，encoder 83.5MB + decoder 30.5MB = **114.0MB**，实测 0.3–2.0s/条） |
| 体积达标方案 | **pix2text-mfr int8 量化版**（社区 Brian314 仓库，encoder 22.0MB + decoder 28.7MB = **50.8MB**，实测速度与 fp32 持平） |
| 精度天花板（本期不建议） | PP-FormulaNet_plus-S（En-BLEU 88.71 / 248MB，但**只有 Paddle 权重、无官方 ONNX**，需 paddle2onnx 转换） |
| 明确不建议 | Texify（596MB + GPL-3.0/CC-BY-SA）、UniMERNet（1.5GB、CPU 8.3s）、PP-OCRv4 server rec（173MB 且精度低于 v5 server） |
| 文字识别升级 | **PP-OCRv5 mobile det(4.6MB) + mobile rec(15.9MB)**，官方 ONNX 现成可用；rec 精度 78.74 → 81.29，det hmean 63.8 → 79.0 |
| 文字升级的代价 | rec 输出类别从 6625 → **18385**，字典从 6623 字 → **18383 字**（官方 inference.yml 内已内嵌）；det 本机实测约 **2.7×** 慢（960×960：98ms → 269ms） |
| 总体积账 | 现状 OCR 15.3MB → 升级后 20.5MB（+5.2MB）；公式 +114MB（fp32）或 +50.8MB（int8） |

---

## 1. 现状与约束

### 1.1 现有管线（读源码确认）

上述实现基于 src/ocr.cpp：

1. resizeBilinear 把整图缩到长边 1280 内、32 对齐，限制 1600×1600 像素；
2. 归一化 (v/255 - 0.5) / 0.5，NCHW float32，**RGB** 顺序；
3. det 推理 → DB 概率图，阈值 0.3 → 2×2 膨胀 → 连通域 → 面积≥12、均分≥0.5 → 映射回原图并外扩；
4. 按行排序后逐框裁切 → **高 48、宽按比例（≤1600）** → rec 推理 → CTC 贪心解码（blank=0，去重复、去 blank）；
5. 字典 ppocr_keys_v1.txt（6623 字）前后补 blank 和空格 → 6625 类。

src/ocr.h 的 OcrLine{text, score, box} 是全项目通用的结果结构；src/ocrdialog.cpp 已经预留了「LaTeX」页（setLatex() / m_latexEdit），也就是说**公式结果的展示层已经存在，缺的只是离线推理后端**。

### 1.2 两个容易踩的细节（升级时必看）

- **归一化不一致**：PaddleOCR 官方 det 预处理是 ImageNet 均值方差（mean 0.485/0.456/0.406，std 0.229/0.224/0.225，**BGR**），而现有代码 det/rec 都用 0.5/0.5 + RGB。现在能跑（DB 对归一化不敏感），但换 v5 模型时建议**按官方参数来**，否则精度打折。
- **rec 输入尺寸**：官方 RecResizeImg 是「保持宽高比 + 右侧补白到 3×48×320」。现有代码是「高 48 + 任意宽」，对动态宽度的 ONNX 也能跑，但补白到 320 的倍数更贴近训练分布。

---

## 2. 公式模型候选对比

| 模型 | 架构 / 参数量 | 官方 ONNX | 权重体积 | License | 输入尺寸 | 输出 | CPU 耗时量级 | 结论 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **pix2text-mfr-1.5** | TrOCR：DeiT-S 编码器（384×384, patch16, 12 层, hidden 384）+ 6 层 Transformer 解码器（d=256, vocab 1868）；≈30M | 有，官方双 ONNX（encoder/decoder） | **114.0MB**（83.5 + 30.5） | **MIT** | 384×384 RGB，mean/std=0.5 | LaTeX（BPE 词表 1868） | **实测 0.3–2.0s**（encoder 98ms + 每 token 10–19ms） | **首选** |
| pix2text-mfr int8 | 同上（v1.0 权重），编码器动态量化；≈30M | 有，社区量化（Brian314） | **50.8MB**（22.0 + 28.7） | MIT | 384×384 | LaTeX（vocab 1200） | **实测 0.3–1.8s**（量化不提速） | **体积达标方案** |
| PP-FormulaNet-s | PP-HGNetV2-B4 + 自回归解码；≈55M | 无，仅 Paddle 静态图 | 224MB | Apache-2.0 | 384×384（UniMERNetImgDecode） | LaTeX（unimernet_tokenizer） | 官方 254ms（CPU 高性能模式） | 精度好，但要自己转 ONNX |
| PP-FormulaNet_plus-S | 同上 + 更多中英数据；≈61M | 无，仅 Paddle 静态图 | 248MB | Apache-2.0 | 384×384 | LaTeX | 官方 261ms | **精度/体积比最佳**，但同样卡在转换 |
| PP-FormulaNet-L / plus-L | Vary_ViT_B + 解码器；≈173M | 无（官方 PP-FormulaNet_plus-L_onnx 仓库为空壳） | 695MB | Apache-2.0 | 384×384 | LaTeX | 官方 3132ms | 体积超标 |
| PP-FormulaNet_plus-M | 同上；≈147M | 无，社区版 566MB（jinzhenj） | 595MB | Apache-2.0 | 384×384 | LaTeX | 官方 1s 级 | 体积超标 |
| LaTeX-OCR（pix2tex） | ResNet/ViT 编码器 + Transformer 解码器；≈33M | 无官方 ONNX（只有 PyTorch） | ≈133MB（fp32） | **MIT** | 672×192（补白） | LaTeX | 估计 0.5–1.5s | 老牌，精度已被 pix2text 超越 |
| **RapidLaTeXOCR** | 上述 LaTeX-OCR 的 ONNX 化 + 图像预缩放模型；≈42M | 有，官方 ONNX（GitHub Release） | **170.6MB**（encoder 84.9 + decoder 48.6 + resizer 37.2） | MIT | 672×192 | LaTeX | 估计 0.5–1.5s | ONNX 可用但比 pix2text 大 56MB、精度更老 |
| Texify | Donut 系（Swin 编码器 + 自回归解码）；≈149M | 无官方 ONNX（社区 onnx-community：int8 仍 301MB） | 596MB | **GPL-3.0**（代码）/ CC-BY-SA-4.0（权重） | 420×420 | LaTeX | 估计 2–5s | 许可传染 + 体积超标，**不建议** |
| UniMERNet | Donut-Swin + mBART；≈390M | 无，仅 Paddle（1.5GB） | 1530MB | Apache-2.0 | 动态 | LaTeX | 官方 **8288ms** | **不建议**（体积 + 速度） |
| （补充）PDFluent formula-onnx | 轻量 encoder/decoder；≈9M | 有，官方 ONNX | 35.7MB | **AGPL-3.0** | — | LaTeX | 未测 | 体积诱人但 AGPL，商业闭源不可用 |
| （补充）nougat-latex-base ONNX | Donut 系；≈120M | 有，社区 | int8 338MB | Apache-2.0 | 420×420 | LaTeX | 估计 3s+ | 体积超标 |

### 2.1 关键判断

1. **官方 ONNX 是硬门槛**。PP-FormulaNet 系列（精度最好、体积最合理）只发布 Paddle 静态图（inference.pdiparams），要转 ONNX 必须装 paddle2onnx + paddlepaddle（约 600MB 工具链）并处理 Paddle 自定义算子；官方 PaddlePaddle/PP-FormulaNet_plus-L_onnx 仓库目前只有 README（0 个权重文件）。本项目不允许第三方依赖，**长链路转换不适合本期**。
2. **≤100MB 的现实解**：只有 pix2text 系（fp32 114MB 略超，int8 50.8MB 达标）和 AGPL 的 PDFluent（35.7MB）。
3. **许可**：pix2text / LaTeX-OCR / RapidLaTeXOCR = MIT（可商用）；PP-FormulaNet / UniMERNet = Apache-2.0；**Texify = GPL-3.0 代码 + CC-BY-SA 权重（传染性）**，闭源分发有风险。

---

## 3. 实测：下载、体积、SHA256、CPU 耗时

测试环境：Windows 11 + onnxruntime **1.31.0**（Python 绑定，CPUExecutionProvider，intra_op_num_threads=8），与项目打包的 onnxruntime-win-x64-1.31.1 同代，数据可直接参考。

### 3.1 公式模型实测

| 模型 | encoder | decoder | 单条公式总耗时 |
| --- | --- | --- | --- |
| pix2text-mfr-1.5 | 384×384：**97.9ms** | 短序列 10.0ms/步；80 token 时 19.4ms/步 | 20 token ≈ **0.30s**；80 token ≈ **1.65s**；100 token ≈ **2.0s** |
| pix2text-mfr int8 | 384×384：**109.2ms** | 短序列 9.9ms/步；80 token 时 16.9ms/步 | 20 token ≈ **0.30s**；80 token ≈ **1.45s** |

要点：

- **int8 只省体积不省时间**：编码器量化后反而慢 11%（109 vs 98ms），因为反量化开销 + 动态量化 kernel 未针对本机优化。若追求速度，**不要**用量化版。
- **decoder 没有 KV cache**（ONNX 输入只有 input_ids + encoder_hidden_states，输出只有 logits），每生成一个 token 都要把整段前缀重跑一遍，耗时随 token 数**超线性**（10ms/步 → 19ms/步）。长公式（>200 token）会到 4s 以上，必须设 token 上限。
- 模型加载：encoder+decoder 合计 **0.77s**（首次）。

### 3.2 文字识别模型实测（同一台机器）

| 模型 | 体积 | 输出类别 | 官方精度 | 官方 CPU 耗时 | 本机实测 |
| --- | --- | --- | --- | --- | --- |
| PP-OCRv4 mobile det（现用） | 4.53MB | — | hmean 63.8 | 56.60 / 20.79 ms | 640²: **35.0ms**；960²: **97.7ms** |
| PP-OCRv5 mobile det | 4.60MB | — | **hmean 79.0** | 57.77 / 28.15 ms | 640²: **73.4ms**；960²: **268.9ms** |
| PP-OCRv4 mobile rec（现用） | 10.35MB | **6625** | acc 78.74 | 5.26 ms | 48×320: **10.2ms** |
| PP-OCRv5 mobile rec | 15.77MB | **18385** | **acc 81.29** | 21.20 / 5.32 ms | 48×320: **9.3ms** |
| PP-OCRv5 server rec | 80.66MB | 18385 | acc 86.38 | 31.21 ms | 未测（同量级 +5–10ms） |
| PP-OCRv4 server rec | 173MB | 6625 | acc 85.19 | 36.93 ms | 未测 |

> 注：官方表格的 CPU 耗时基于 paddle_static 引擎，与 ORT 实测不完全可比；det 的 2.7× 差距在本机稳定复现（两次独立测量），属于**架构差异**（v5 det 末尾是 ConvTranspose 上采样，中间张量更大），不是噪声。

### 3.3 冒烟测试：模型真的能出 LaTeX

用 PIL 把纯文本公式渲染成图（Segoe UI 64px，非 LaTeX 排版），按 6.1/6.2 的步骤走完整链路（384×384 → 归一化 → encoder → 贪心解码 → BPE 解码），结果：

| 输入图像内容 | 模型输出 | token 数 |
| --- | --- | --- |
| x² + y² = r² | x ^ { 2 } + y ^ { 2 } = r ^ { 2 } | 17 |
| α + β = γ | \alpha + \beta = \gamma | 8 |
| a/b + c/d = 1 | a / \mathrm { b } + c / \mathrm { d } = \mathrm { 1 } | 21 |

这说明：

- **链路可行**：C++ 侧只要实现「BPE 词表 + Ġ→空格」就能得到正确 LaTeX，不需要完整的 transformers/tokenizers 依赖。
- **输出带空格且常包 \mathrm**：`x ^ { 2 }`、`\mathrm { b }` 这种写法渲染没问题，但可读性差；6.3 的「空白规整」是**必需**的，不是可选优化。
- **token 数很短**（8–21），真实耗时 ≈ 0.2–0.4s，比按 100 token 估算的 2s 乐观得多；只有长公式才会逼近 2s。
- 渲染字体与训练分布（LaTeX 排版）差异很大仍能识别，说明模型对字体/分辨率有一定鲁棒性；但这也只是冒烟测试，**不等于准确率**。

---

## 4. 文字识别候选对比（体积 / 适用场景）

| 模型 | 体积 | 精度 | 适用场景 | 建议 |
| --- | --- | --- | --- | --- |
| PP-OCRv4 mobile det | 4.5MB | hmean 63.8 | 现有基线，小字/密排漏检多 | 可替换 |
| **PP-OCRv5 mobile det** | **4.6MB** | **hmean 79.0** | 截图、UI、文档混排，召回显著提升 | **推荐**（代价是 2.7× 慢，可降采样到长边 640–800 折中） |
| PP-OCRv5 server det | 84.3MB | hmean 83.8 | 高精度文档扫描 | 体积超标，不建议端侧 |
| PP-OCRv4 mobile rec | 10.3MB | acc 78.74 | 现有基线，6625 类 | 可替换 |
| **PP-OCRv5 mobile rec** | **15.9MB** | **acc 81.29** | 简/繁/英/日 + 手写、竖排、生僻字；单模型多语 | **推荐**（+5.6MB 换 +2.55 点） |
| PP-OCRv5 server rec | 80.7MB | acc 86.38 | 文档、票据等追求精度 | 备选（+65MB 内存） |
| PP-OCRv4 server rec | 173MB | acc 85.19 | — | **不建议**（比 v5 server 又大又差） |
| PP-OCRv6 small rec | 20.3MB | 81.3* | 50 语种，2026 新模型（PPLCNetV4 + LightSVTR + CTC/NRTR） | 观察项（*指标评估集不同，不可直接对比） |
| PP-OCRv6 medium rec | 73.3MB | 83.2* | 服务端多语 | 体积超标 |

**推荐组合**：PP-OCRv5 mobile det + PP-OCRv5 mobile rec（合计 20.4MB）。若对延迟敏感，可保留 v4 det、只换 v5 rec —— **rec 是纯收益**（更快 + 更准 + 多语），det 则是「召回换延迟」的取舍。

---

## 5. 推荐表

| 档位 | 方案 | 理由 |
| --- | --- | --- |
| **首选** | **pix2text-mfr-1.5（fp32 ONNX）** | 唯一「官方 ONNX + MIT + 体积可接受 + 有公开精度背书」的组合；114MB 只超预算 14MB；编码器 98ms、典型公式 0.3–0.8s，交互可接受；词表 1868 全 ASCII，C++ 解码只需处理 Ġ→空格 |
| **备选（体积硬约束时）** | pix2text-mfr int8（50.8MB） | 达标 ≤100MB，速度与 fp32 持平；但它是 v1.0 权重 + 社区量化，精度未验证，且词表只有 1200 → 复杂公式掉点风险更高 |
| 备选（精度优先，需额外工期） | PP-FormulaNet_plus-S（248MB Paddle） | En-BLEU 87–88.7，官方 261ms，Apache-2.0；但要引入 paddle2onnx 转换流程，且体积 2 倍于预算 |
| 观察项 | PP-OCRv6 small rec（20.3MB，官方 ONNX） | 新架构、多语种，等官方精度表补齐后再评估 |
| **不建议** | Texify | 596MB + GPL-3.0 传染 + 无官方 ONNX |
| **不建议** | UniMERNet | 1.5GB、CPU 8.3s，端侧不可用 |
| **不建议** | PP-OCRv4 server rec | 173MB 却不如 81MB 的 v5 server |
| **不建议** | PDFluent formula-onnx | 35.7MB 很香，但 **AGPL-3.0**，闭源分发不可行 |
| **不建议** | RapidLaTeXOCR | 170.6MB（含 37MB 图像预缩放模型）+ 老架构，被 pix2text 全面压制 |

---

## 6. 接入建议

### 6.1 输入预处理（公式）

    QImage 裁切（行框外扩 2–4px）
      → 白底 pad 成正方形（避免长公式被横向压扁）
      → 双三次缩放到 384×384
      → RGB888 拆平面（注意 Qt 的 Format_RGB888 已是 RGB 序）
      → float: (v/255 - 0.5) / 0.5
      → NCHW [1,3,384,384]

- 官方 preprocessor 是「直接 resize 到 384×384」（DeiTImageProcessor，do_center_crop=false，mean/std=0.5）。先 pad 再缩放与官方略有差异，**建议做 A/B 对比**；对超宽公式（宽高比 > 6）尤其值得试。
- 高度 < 16px 或面积 < 200px² 的框直接跳过 —— 模型看不清，只会产生幻觉 token。

### 6.2 解码（C++ 侧循环）

    ids = [1]                        // <s> = decoder_start
    for step in 0..maxTokens-1:
        logits = decoder.Run(input_ids=ids, encoder_hidden_states=enc)   // [1, T, 1868]
        next = argmax(logits[0, T-1, :])
        if next == 2: break          // </s>
        ids.append(next)

- 词表约定：0=<pad> 1=<s> 2=</s> 3=<unk> 4=<mask>，其余为 BPE token。
- **必须设上限**：官方 1024，建议 512（最坏约 10s），并且每 32 步检查一次「取消」标志，避免 UI 卡死。
- 性能优化：decoder 无 KV cache，序列越长越慢；**别**试图 batch 多条公式（收益低、内存翻倍）。可做的只有「限制 token 数」和「复用 encoder session」。
- 词表解码：BPE ByteLevel，token 里的 Ġ(U+0120) → 空格，Ċ(U+010A) → 换行；LaTeX 主要是 ASCII，直接拼接即可，不需要完整 GPT-2 byte-decoder 表。

### 6.3 输出后处理（LaTeX 清理）

按顺序做（每步都可单测）：

1. **去壳**：trim()；去掉成对的 $...$ / $$...$$ / \[...\]。
2. **去特殊 token 残留**：<s> <pad> </s> <unk> <mask>。
3. **空白规整**：
   - 连续空白 → 单空格；
   - \left ( → \left(、\right ) → \right)（命令后不留空格）；
   - { } 空组删除；\mathrm { x } → \mathrm{x}（可选，影响渲染一致性）。
4. **括号平衡**：统计 { / }，不平衡时按「末尾补 }」或「截断到最后一个完整组」处理，并标记低置信。
5. **常见误识别修正**（可选白名单）：
   - \operatorname* → \operatorname；
   - \text { } 内含中文标点 → 原样保留（LaTeX 渲染会报错时可替换为 \mathrm）；
   - Unicode 数学符号（− × ≤ ≥ ∑ ∫ α）→ 对应 LaTeX 命令（- \times \leq \geq \sum \int \alpha）。
6. **置信度**：记录每步 argmax 概率，取几何平均 exp(mean(log p))；< 0.6 时在 UI 标注「可能不准」。注意 softmax 后的概率不能直接平均算术值。
7. **结果结构**：建议新增 struct FormulaLine { QString latex; float score; QRect box; };（**不要**改 OcrLine，避免牵连 overlay / translate / 导出等既有链路）。

### 6.4 与现有 det → 判断 → 分派管线如何衔接

分三步走，风险从低到高：

**方案 A（推荐先落地，改动最小）——「整图/选区公式」直通**

- 触发：Overlay 右键菜单新增「识别公式」，或 OcrDialog 里加「按公式识别」按钮。
- 流程：截图/选区 →（可选：只做白底 pad）→ MFR → OcrDialog::setLatex()（接口已存在）。
- 优点：**零误判、零回归**，不碰 det/rec；缺点：一次只认一条公式。
- 适用：截图工具的高频场景（截一条公式贴到笔记里）。

**方案 B（混合分派）——det 出框，逐框判断**

    det → 行框列表
      └─ 逐个判断 isFormula(box, crop, recText, recScore)
            ├─ 是 → MFR(crop) → FormulaLine
            └─ 否 → rec(crop) → OcrLine

isFormula 的启发式（建议 3 条命中 2 条）：

- 行高 / 该行中位字高 > 1.4（公式有上下标、根号、分式，通常比正文高）；
- rec 文本中数学符号占比 > 15%（= + − × ÷ ∑ ∫ √ ≤ ≥ ^ _ { } α β θ π）；
- rec 平均置信度 < 0.55 且文本含数字/符号（正文识别失败，多半就是公式）。

注意：

- 公式框**不要**用现在的大外扩（pady = 0.45*h），会带进上下相邻正文；公式建议 pad = 2–4px 原样裁。
- 误判时用户会看到 LaTeX 乱码，需要有「切换回文字」的入口。

**方案 C（整页公式检测，本期不做）**

- 引入 pix2text-mfd（yolo11m，ONNX 约 50MB）先检测公式区域，再逐区域 MFR；准确率最高，但模型 +50MB、多一次推理，且与「截图工具」的心智模型不匹配。

### 6.5 内存、线程、生命周期

- 常驻内存：encoder 87.5MB + decoder 32MB 权重 + ORT arena ≈ **150MB**；比现有 OCR（15MB）大一个量级。
- **懒加载 + 空闲释放**：沿用 Ocr 单例那套 init()/release()，第一次用到公式才加载，闲置 5 分钟释放；否则小内存机器会明显变卡。
- 线程：SetIntraOpNumThreads(min(4, idealThreadCount()/2))；decoder 单步是「小矩阵 × 长序列」，超过 4 线程收益递减。
- 加载耗时 0.77s，建议放到工作线程并显示「正在加载公式模型…」。

### 6.6 打包与降级

- 目录：models/pix2text_mfr_encoder.onnx、pix2text_mfr_decoder.onnx、pix2text_mfr_tokenizer.json、pix2text_mfr_preproc.json。
- 安装包从 ~30MB 涨到 ~145MB（fp32）或 ~80MB（int8）。建议**做成可选组件**或在设置里首次使用时下载。
- 降级：模型缺失时 OcrDialog 的 LaTeX 页保持现有占位文案「该图未检测到公式」，不能崩、不能阻塞主流程（现有 init() 的 false 分支已经这么设计，沿用即可）。
- 与在线 VLM（VisionClient）的关系：在线识别保留为「云端高精度」选项，离线 MFR 作为**隐私模式 / 断网 fallback**；建议设置项三选一：关闭 / 本地 ONNX / 在线模型。

---

## 7. 下载记录

工具：tools/formula_eval/fetch_models.py（Python 标准库，支持 --dry-run、断点续传、SHA256 校验、manifest）。落盘目录 dl/models/。

### 7.1 成功（HTTP 200，直连 HuggingFace，平均 0.6MB/s）

| 模型 | 文件 | 字节 | SHA256 |
| --- | --- | --- | --- |
| pix2text-mfr-1.5 | encoder_model.onnx | 87,510,770 | 080a3f660f08bc9ebcacdd96e34be6b6400f8c7e62d7cd0dd8251badc37f610b |
| pix2text-mfr-1.5 | decoder_model.onnx | 32,026,253 | 917deb98e91a0453c5f234f58a0f32f9fb037de8527c7eb4ed394daf9e692f2a |
| pix2text-mfr-1.5 | tokenizer.json | 113,168 | 4ffbeb2143e6a38324bb6111b7a8109530d38a076a8439aa5777535f0a32758a |
| pix2text-mfr-1.5 | config.json | 1,573 | fe4076f08f6ca75940f6af9268d51928b834979a69bc2145dacee62633a5d53d |
| pix2text-mfr-1.5 | preprocessor_config.json | 450 | 36a945a7cc645688b9ef64dabae16979cf5f7c1c448569cc306694edc0598b9b |
| pix2text-mfr-1.5 | generation_config.json | 211 | 7363c031c6142d35a276815b0e285cc289dfb9f51d0b7c63de8f3ed65cc8d8ad |
| pix2text-mfr int8 | encoder_model.onnx | 23,083,189 | 5e5141ed5f6e05851b1a38b6df85fe17c1dcb779358729fa707f9ee36b7b9dd9 |
| pix2text-mfr int8 | decoder_model.onnx | 30,114,937 | fd0f92d7a012f3dae41e1ac79421aea0ea888b5a66cb3f9a004e424f82f3daed |
| pix2text-mfr int8 | tokenizer.json | 39,161 | 3e2ab757277d22639bec28c9d7972e352d3d1dba223051fa674002dc5ab64df3 |
| pix2text-mfr int8 | config.json | 4,564 | 3f8c512e902bc9963ce6c2ab7c31d13a7a4aa2a72687c5530f620454da8c3858 |
| PP-OCRv5 mobile det | inference.onnx | 4,826,518 | a431985659dc921974177a95adcfbb90fd9e51989a5e04d70d0b75f597b6e61d |
| PP-OCRv5 mobile rec | inference.onnx | 16,534,782 | da72dc72ca4dc220df0dfde68c1dedc31c58d3e76a25871122e5056227d50092 |

完整记录（含每文件耗时、URL、状态码）见 dl/models/manifest.json。

下载后已用 onnxruntime 逐个加载验证 IO：

- pix2text-1.5：encoder 输入 pixel_values [B,3,H,W] → 输出 last_hidden_state [B,578,384]；decoder 输入 input_ids [B,T] + encoder_hidden_states [B,578,384] → 输出 logits [B,T,1868]。
- int8：同上，但 logits 最后一维是 1200（v1.0 词表）。
- PP-OCRv5 mobile det：输入 x [B,3,H,W]（动态）→ 输出 [B,1,H,W] 概率图，与现有 DB 后处理兼容。
- PP-OCRv5 mobile rec：输入 x [B,3,48,W]（动态）→ 输出 [B,T,18385]，CTC 后处理与现有逻辑一致，只换字典。

### 7.2 失败 / 不可用

| 目标 | 现象 | 说明 |
| --- | --- | --- |
| PaddlePaddle/PP-FormulaNet_plus-L_onnx | 仓库存在但**只有 README**，0 个权重 | 官方尚未真正发布 FormulaNet 的 ONNX |
| RapidAI/RapidLaTeXOCR（HF） | **HTTP 401** | 仓库不可匿名访问；实际权重在 GitHub Release v0.0.0（encoder 84.88MB / decoder 48.59MB / image_resizer 37.16MB / models.zip 156.42MB） |
| opendatalab/UniMERNet（HF） | **HTTP 401** | 需授权；官方权重在 wanderkid/unimernet_base（1.3GB） |
| PaddlePaddle/LaTeX_OCR_rec | **HTTP 401** | 需授权；且只有 Paddle 格式（97.6MB pdiparams），无 ONNX |
| PaddlePaddle/PP-FormulaNet_plus-S | 未下载（有意跳过） | 245MB Paddle 权重，本机无法转换，下载无意义 |

> 网络侧备注：本机 curl.exe / Invoke-WebRequest 走 schannel 报 SEC_E_NO_CREDENTIALS，**只有 Python(OpenSSL) 的 urllib 能出网** —— 所以脚本用 urllib 而不是 curl。

### 7.3 顺带发现

- models/ 目录下 4 个哈希命名文件（4.7MB / 9.9MB / 16.6MB / 21.2MB）**无法被 onnxruntime 解析**（INVALID_PROTOBUF），疑似历史遗留的未完成下载；真正生效的是 exe 同目录 models/（dist/TackShot/models/ch_PP-OCRv4_*.onnx）。建议确认后清理，避免误导。
- PP-OCRv5 rec 的 18383 字典**已内嵌在官方 inference.yml 里**（147KB），不需要另外下载 ppocrv5_dict.txt。

---

## 8. 复现命令

    cd C:\Users\laiki\.dsh\workspace\tackshot

    # 1) 只看计划（不联网、不写盘）
    python tools/formula_eval/fetch_models.py --dry-run

    # 2) 下载两个公式模型（默认只下 formula 类）
    python tools/formula_eval/fetch_models.py

    # 3) 连文字识别模型一起下
    python tools/formula_eval/fetch_models.py --all

    # 4) 只校验已下载文件的 SHA256
    python tools/formula_eval/fetch_models.py --verify

    # 5) 国内网络走镜像
    set HF_ENDPOINT=https://hf-mirror.com
    python tools/formula_eval/fetch_models.py

---

## 9. 风险与待验证

1. **精度未在真实截图上验证**：本报告只验证了「能加载、能跑、IO 形状/词表对得上」，没有跑公式测试集。建议用 20–30 条真实截图做一次 CER 对比（pix2text fp32 vs int8）。
2. **114MB 超预算 14MB**：若硬性 ≤100MB，只能走 int8（50.8MB）。建议把「≤100MB」理解为「安装包可接受范围」，则 fp32 版可接受。
3. **长公式慢**：无 KV cache，200 token 以上 > 4s。UI 必须有 loading 和取消。
4. **中文/手写公式**：pix2text-mfr 词表 1868 全英文 LaTeX 记号，中文公式（如 \text{面积}）大概率丢字；PP-FormulaNet_plus-M/L 才支持中文。截图工具的公式以印刷体英文为主，可接受。
5. **PP-OCRv5 det 变慢 2.7×**：需在真实截图上测端到端延迟再决定是否换 det；rec 单独升级是低风险高收益。
6. **许可复核**：MIT/Apache-2.0 结论来自 GitHub/HF 元数据，正式发布前建议再看一眼 LICENSE 原文（尤其 int8 社区仓库不附带 LICENSE 文件）。
