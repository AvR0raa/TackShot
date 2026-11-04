import io

# ---------------- config ----------------
p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\config.h"
s = io.open(p, encoding="utf-8").read()
if "baiduAppId" not in s:
    s = s.replace('    QString visionProvider = "gemini";',
'''    QString baiduAppId;                         // 百度翻译开放平台 APPID
    QString baiduSecret;                        // 百度翻译密钥（DPAPI 存密钥）
    int     baiduPaste = 1;                     // 0 关闭贴合 / 1 整图 / 2 分块
    QString simpleTexToken;                     // SimpleTex UAT（DPAPI 存）
    QString visionProvider = "gemini";''')
io.open(p, "w", encoding="utf-8").write(s)

p = r"C:\Users\laiki\.dsh\workspace\tackshot\src\config.cpp"
s = io.open(p, encoding="utf-8").read()
if "baiduAppId" not in s:
    s = s.replace('    o["visionProvider"] = visionProvider;',
'''    o["baiduAppId"] = baiduAppId;
    o["baiduPaste"] = baiduPaste;
    o["visionProvider"] = visionProvider;''')
    s = s.replace('    if (o.contains("visionProvider")) visionProvider = o["visionProvider"].toString();',
'''    if (o.contains("baiduAppId")) baiduAppId = o["baiduAppId"].toString();
    if (o.contains("baiduPaste")) baiduPaste = o["baiduPaste"].toInt();
    if (o.contains("visionProvider")) visionProvider = o["visionProvider"].toString();''')
io.open(p, "w", encoding="utf-8").write(s)
print("config: baidu + simpletex fields")
