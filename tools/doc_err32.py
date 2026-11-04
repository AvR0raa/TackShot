import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\docs\VERIFY.md"
v = io.open(p, encoding="utf-8").read()
v += """
## 23. 安装失败排查（err=32 文件占用）

用户报“安装失败”，日志定位：

    create failed err=32 target=...\\Qt6Core.dll
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
"""
io.open(p, "w", encoding="utf-8").write(v)
print("verify updated")
