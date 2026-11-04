import socket, subprocess, os
for h in ["www.7-zip.org", "download.qt.io", "github.com"]:
    try:
        print(h, "->", socket.gethostbyname(h))
    except Exception as e:
        print(h, "ERR", e)
print("tar:", subprocess.run(["where", "tar"], capture_output=True, text=True).stdout.strip() or "not found")
print("vers:", subprocess.run(["tar", "--version"], capture_output=True, text=True).stdout.strip()[:80])
