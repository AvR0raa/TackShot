import io
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\main.cpp"
s = io.open(p, encoding="utf-8").read()
old = """        auto r1 = client.translateLong(QStringLiteral("Hello, world"), QStringLiteral("简体中文"),
                                       p, "sk-test", QString(), 1500, false);"""
new = """        TranslateCache::get().clear();
        auto r1 = client.translateLong(QStringLiteral("Hello, world"), QStringLiteral("简体中文"),
                                       p, "sk-test", QString(), 1500, true);"""
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("cache test fixed")
else:
    print("MISS")
