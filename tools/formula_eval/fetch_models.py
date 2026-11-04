#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TackShot 公式/文字识别模型抓取脚本（可重复执行）。

用法示例：
    python tools/formula_eval/fetch_models.py --dry-run
    python tools/formula_eval/fetch_models.py --only pix2text-mfr-1.5
    python tools/formula_eval/fetch_models.py --all
    python tools/formula_eval/fetch_models.py --verify

设计要点：
    1) 只用 Python 标准库（urllib / hashlib / json / argparse），不引入第三方依赖；
    2) 断点续传：中断后重跑会从 .part 文件继续；
    3) 每下载完一个文件立刻算 SHA256，并把结果写入 dest/manifest.json；
    4) --dry-run 只打印计划，不产生任何网络请求与磁盘写入；
    5) 可用环境变量 HF_ENDPOINT 切换镜像（如 https://hf-mirror.com）。

注意：本脚本只负责下载，不加载模型。模型是否真能跑由 onnxruntime 验证。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional

# HuggingFace 端点：国内网络可用 HF_ENDPOINT=https://hf-mirror.com 加速
HF_ENDPOINT = os.environ.get("HF_ENDPOINT", "https://huggingface.co").rstrip("/")

# 项目根目录（tools/formula_eval/ 往上两级）
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DEST = os.path.join(ROOT, "dl", "models")

CHUNK = 256 * 1024


class ModelFile:
    """单个模型文件的描述。"""

    def __init__(self, path: str, size: int, sha256: Optional[str] = None):
        self.path = path          # 仓库内相对路径
        self.size = size          # 字节数（已知则为校验依据）
        self.sha256 = sha256      # 已知哈希（可选）

    def url(self, repo: str) -> str:
        return "%s/%s/resolve/main/%s" % (HF_ENDPOINT, repo, self.path)


class ModelEntry:
    """一个模型候选（可能由多个文件组成）。"""

    def __init__(self, name: str, kind: str, repo: str, arch: str, license_: str,
                 note: str, files: List[ModelFile], priority: int):
        self.name = name
        self.kind = kind          # formula / ocr
        self.repo = repo
        self.arch = arch
        self.license = license_
        self.note = note
        self.files = files
        self.priority = priority  # 1 = 最高优先

    def total_size(self) -> int:
        return sum(f.size for f in self.files)


# ---------------------------------------------------------------------------
# 模型清单（体积数据来自 HuggingFace tree API 实测，2026-11 核对）
# ---------------------------------------------------------------------------
MODELS: List[ModelEntry] = [
    ModelEntry(
        name="pix2text-mfr-1.5",
        kind="formula",
        repo="breezedeus/pix2text-mfr-1.5",
        arch="TrOCR：DeiT-S 编码器(384x384, patch16, 12层) + 6 层 Transformer 解码器(d=256, vocab=1868)",
        license_="MIT",
        note="首选。官方直接发布 ONNX（encoder/decoder 分离），CPU 可跑，许可宽松。",
        priority=1,
        files=[
            ModelFile("encoder_model.onnx", 87510770,
                      "080a3f660f08bc9ebcacdd96e34be6b6400f8c7e62d7cd0dd8251badc37f610b"),
            ModelFile("decoder_model.onnx", 32026253,
                      "917deb98e91a0453c5f234f58a0f32f9fb037de8527c7eb4ed394daf9e692f2a"),
            ModelFile("tokenizer.json", 113168,
                      "4ffbeb2143e6a38324bb6111b7a8109530d38a076a8439aa5777535f0a32758a"),
            ModelFile("config.json", 1573,
                      "fe4076f08f6ca75940f6af9268d51928b834979a69bc2145dacee62633a5d53d"),
            ModelFile("preprocessor_config.json", 450,
                      "36a945a7cc645688b9ef64dabae16979cf5f7c1c448569cc306694edc0598b9b"),
            ModelFile("generation_config.json", 211,
                      "7363c031c6142d35a276815b0e285cc289dfb9f51d0b7c63de8f3ed65cc8d8ad"),
        ],
    ),
    ModelEntry(
        name="pix2text-mfr-int8",
        kind="formula",
        repo="Brian314/pix2text-mfr-quantized",
        arch="同 pix2text-mfr（v1.0 权重），编码器 int8 动态量化",
        license_="MIT（模型本体）",
        note="次选。唯一能压到 100MB 以内的现成 ONNX 方案，编码器已量化。",
        priority=2,
        files=[
            ModelFile("encoder_model.onnx", 23083189,
                      "5e5141ed5f6e05851b1a38b6df85fe17c1dcb779358729fa707f9ee36b7b9dd9"),
            ModelFile("decoder_model.onnx", 30114937,
                      "fd0f92d7a012f3dae41e1ac79421aea0ea888b5a66cb3f9a004e424f82f3daed"),
            ModelFile("tokenizer.json", 39161,
                      "3e2ab757277d22639bec28c9d7972e352d3d1dba223051fa674002dc5ab64df3"),
            ModelFile("config.json", 4564,
                      "3f8c512e902bc9963ce6c2ab7c31d13a7a4aa2a72687c5530f620454da8c3858"),
            ModelFile("preprocessor_config.json", 450,
                      "36a945a7cc645688b9ef64dabae16979cf5f7c1c448569cc306694edc0598b9b"),
            ModelFile("generation_config.json", 210,
                      "cbea88288d5576a9655ad04e2456768544be22273a1c5ca160e0d16384639b4f"),
        ],
    ),
    ModelEntry(
        name="ppocrv5-mobile-det",
        kind="ocr",
        repo="PaddlePaddle/PP-OCRv5_mobile_det_onnx",
        arch="PP-OCRv5 mobile 检测（DB++，输入 3xH x W，H/W 为 32 的倍数）",
        license_="Apache-2.0",
        note="文字检测升级项，官方 ONNX，体积与现有 v4 det 持平。",
        priority=3,
        files=[
            ModelFile("inference.onnx", 4826518,
                      "a431985659dc921974177a95adcfbb90fd9e51989a5e04d70d0b75f597b6e61d"),
            ModelFile("inference.yml", 903,
                      "98069072e1b6b37d727fd9d9f11725faa46d6ea0de012f2ed26caea011c37699"),
        ],
    ),
    ModelEntry(
        name="ppocrv5-mobile-rec",
        kind="ocr",
        repo="PaddlePaddle/PP-OCRv5_mobile_rec_onnx",
        arch="PP-OCRv5 mobile 识别（SVTR-LCNet + CTC，输入 3x48xW）",
        license_="Apache-2.0",
        note="文字识别升级项，官方 ONNX，比现有 v4 rec(10.3MB) 精度更高。",
        priority=4,
        files=[
            ModelFile("inference.onnx", 16534782,
                      "da72dc72ca4dc220df0dfde68c1dedc31c58d3e76a25871122e5056227d50092"),
            ModelFile("inference.yml", 148345,
                      "5dfeb2777f6d0db8177d8128a8acfcf6e6276dc4ac73ea3bf0dc06d6a5e85d8e"),
        ],
    ),
]


def human(n: int) -> str:
    """字节数转可读字符串。"""
    if n >= 1024 * 1024:
        return "%.2f MB" % (n / 1048576.0)
    if n >= 1024:
        return "%.1f KB" % (n / 1024.0)
    return "%d B" % n


def sha256_of(path: str) -> str:
    """流式计算文件 SHA256。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def is_done(dest_path: str, mf: ModelFile) -> bool:
    """判断文件是否已完整下载。"""
    if not os.path.exists(dest_path):
        return False
    size = os.path.getsize(dest_path)
    # 允许 ±1% 误差：部分文件在 HF 上登记的大小与实际略有出入
    if mf.size and abs(size - mf.size) > max(1024, mf.size // 100):
        return False
    if mf.sha256 and sha256_of(dest_path) != mf.sha256:
        return False
    return True


def download(repo: str, mf: ModelFile, dest_path: str, timeout: int = 60) -> Dict:
    """下载单个文件，支持断点续传；返回记录字典。"""
    url = mf.url(repo)
    part = dest_path + ".part"
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    have = os.path.getsize(part) if os.path.exists(part) else 0
    headers = {"User-Agent": "TackShot-model-fetch/1.0"}
    if have:
        headers["Range"] = "bytes=%d-" % have

    t0 = time.time()
    rec = {"file": mf.path, "url": url, "status": None, "bytes": 0, "sha256": None,
           "elapsed_s": 0.0, "error": None}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            rec["status"] = resp.status
            total = int(resp.headers.get("Content-Length") or 0) + have
            mode = "ab" if (have and resp.status == 206) else "wb"
            if mode == "wb":
                have = 0
            with open(part, mode) as f:
                got = have
                while True:
                    b = resp.read(CHUNK)
                    if not b:
                        break
                    f.write(b)
                    got += len(b)
                    if total:
                        pct = 100.0 * got / total
                        sys.stdout.write("\r    %-44s %6.1f%%  %s / %s   " %
                                         (os.path.basename(mf.path), pct, human(got), human(total)))
                        sys.stdout.flush()
        sys.stdout.write("\n")
        if os.path.exists(dest_path):
            os.remove(dest_path)
        os.replace(part, dest_path)
        rec["bytes"] = os.path.getsize(dest_path)
        rec["sha256"] = sha256_of(dest_path)
        rec["elapsed_s"] = round(time.time() - t0, 1)
    except urllib.error.HTTPError as e:
        sys.stdout.write("\n")
        rec["status"] = e.code
        rec["error"] = "HTTP %d %s" % (e.code, e.reason)
    except Exception as e:  # 网络/磁盘异常都记录，不中断整体流程
        sys.stdout.write("\n")
        rec["error"] = "%s: %s" % (type(e).__name__, e)
    return rec


def load_manifest(path: str) -> Dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_manifest(path: str, data: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def print_plan(entries: List[ModelEntry], dest: str) -> None:
    """打印下载计划（--dry-run 与正常模式都会调用）。"""
    print("下载目录：%s" % dest)
    print("HF 端点：%s" % HF_ENDPOINT)
    total = 0
    for m in entries:
        print("\n[%s] %s  (%s, %s, 优先级 %d)" % (m.kind, m.name, m.arch[:48], m.license, m.priority))
        print("    仓库：%s" % m.repo)
        print("    说明：%s" % m.note)
        for f in m.files:
            dst = os.path.join(dest, m.name, f.path)
            mark = "已存在" if is_done(dst, f) else "待下载"
            print("      %-28s %10s  [%s]" % (f.path, human(f.size), mark))
            if mark == "待下载":
                total += f.size
    print("\n合计需要下载：%s" % human(total))


def main() -> int:
    ap = argparse.ArgumentParser(description="TackShot 公式/文字识别 ONNX 模型抓取工具")
    ap.add_argument("--dest", default=DEFAULT_DEST, help="模型落盘目录，默认 dl/models")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不下载不写盘")
    ap.add_argument("--only", action="append", default=[], help="只处理指定模型名，可重复")
    ap.add_argument("--all", action="store_true", help="包含文字识别模型（默认只下公式模型）")
    ap.add_argument("--verify", action="store_true", help="只校验已存在文件的 SHA256 并打印")
    ap.add_argument("--list", action="store_true", help="列出清单后退出")
    args = ap.parse_args()

    dest = os.path.abspath(args.dest)
    entries = [m for m in MODELS if args.all or m.kind == "formula" or args.only]
    if args.only:
        wanted = set(args.only)
        entries = [m for m in MODELS if m.name in wanted]
    entries.sort(key=lambda m: m.priority)

    if args.list:
        for m in MODELS:
            print("%-22s %-8s %-6s %8s  %s" % (m.name, m.kind, m.license, human(m.total_size()), m.repo))
        return 0

    if args.verify:
        bad = 0
        for m in entries:
            for f in m.files:
                p = os.path.join(dest, m.name, f.path)
                if not os.path.exists(p):
                    print("缺失  %s" % p)
                    bad += 1
                    continue
                print("%-9s %-24s %10s  %s" % ("OK" if is_done(p, f) else "不匹配",
                                              f.path, human(os.path.getsize(p)), sha256_of(p)))
        return 1 if bad else 0

    print_plan(entries, dest)
    if args.dry_run:
        print("\n（--dry-run：未产生任何下载与写入）")
        return 0

    manifest_path = os.path.join(dest, "manifest.json")
    manifest = load_manifest(manifest_path)
    manifest.setdefault("endpoint", HF_ENDPOINT)
    manifest.setdefault("models", {})

    failed = 0
    for m in entries:
        print("\n===== %s =====" % m.name)
        mrec = manifest["models"].setdefault(m.name, {
            "repo": m.repo, "arch": m.arch, "license": m.license, "note": m.note, "files": {},
        })
        for f in m.files:
            dst = os.path.join(dest, m.name, f.path)
            if is_done(dst, f):
                print("  跳过（已存在）：%s  %s" % (f.path, human(os.path.getsize(dst))))
                mrec["files"][f.path] = {
                    "size": os.path.getsize(dst),
                    "sha256": sha256_of(dst),
                    "status": "cached",
                }
                continue
            print("  下载：%s  %s" % (f.path, human(f.size)))
            rec = download(m.repo, f, dst)
            mrec["files"][f.path] = rec
            if rec["error"]:
                failed += 1
                print("  失败：%s -> %s" % (f.path, rec["error"]))
            else:
                print("  完成：%s  %s  sha256=%s" % (f.path, human(rec["bytes"]), rec["sha256"]))
            save_manifest(manifest_path, manifest)

    save_manifest(manifest_path, manifest)
    print("\n清单已写入：%s" % manifest_path)
    if failed:
        print("有 %d 个文件失败，详见 manifest.json" % failed)
        return 1
    print("=== 全部完成 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
