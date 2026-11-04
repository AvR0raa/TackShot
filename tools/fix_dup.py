import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\setup\setup_w32.cpp"
s = io.open(p, encoding="utf-8").read()
s = s.replace("static std::vector<Entry> g_entries;\nstatic std::wstring g_self;\n",
              "static std::vector<Entry> g_entries;\n", 1)
io.open(p, "w", encoding="utf-8").write(s)
print("duplicate removed")
