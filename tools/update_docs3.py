import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\docs\VERIFY.md"
v = io.open(p, encoding="utf-8").read()
v += """
## 11. 撤销 / 重做

命令：TackShot.exe --undo-selftest build\\undo.txt

    counts=3,2,1,2

连续加 3 个标注 → 撤销两次剩 1 个 → 重做一次回到 2 个，栈行为符合预期。

## 12. 最终安装包

    安装器 68.22 MB  ->  install=0  files=32  MB=68.1
    安装后跑 --undo-selftest / --longshot-selftest / --gif-selftest 均通过
"""
io.open(p, "w", encoding="utf-8").write(v)
print("ok")
