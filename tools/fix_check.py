import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\tools\check_mp4.py"
s = io.open(p, encoding="utf-8").read()
s = s.replace('entry = data[p4+h4+8:p4+h4+8+4]', 'entry = data[p4+h4+8+4:p4+h4+8+8]')
io.open(p, "w", encoding="utf-8").write(s)
print("checker fixed")
