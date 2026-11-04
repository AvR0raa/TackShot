import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\README.md"
s = io.open(p, encoding="utf-8").read()
s = s.replace("（32 个文件 ≈ 136 MB，含 onnxruntime 与 OCR 模型）", "（32 个文件 ≈ 68 MB，含 onnxruntime 与 OCR 模型；独立 Uninstall.exe 仅 22 KB）")
s = s.replace("- 撤销只支持逐级回退，没有重做栈上限管理。", "- 撤销/重做只保留最近一步（单步）。")
io.open(p, "w", encoding="utf-8").write(s)
print("ok")
