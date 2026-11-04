import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\setup\setup_w32.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("    vfwprintf(buf, fmt, ap);", "    vswprintf(buf, 2048, fmt, ap);")
io.open(p, "w", encoding="utf-8").write(s)
print("fixed")
