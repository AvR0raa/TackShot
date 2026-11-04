import json, urllib.request

def post(path, system, user="hello"):
    body = json.dumps({"model":"m","messages":[{"role":"system","content":system},
                                               {"role":"user","content":user}],
                       "temperature":0.2,"stream":False}).encode()
    req = urllib.request.Request("http://127.0.0.1:8899" + path, data=body,
                                 headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

print("stats:", urllib.request.urlopen("http://127.0.0.1:8899/stats", timeout=10).read().decode())
r = post("/v1/ok/chat/completions", "规则\n5) 必须遵守以下术语表（左为原文，右为指定译法）：\nTackShot=塔克肖特", "TackShot is great")
print("with glossary:", r["choices"][0]["message"]["content"])
r2 = post("/v1/ok/chat/completions", "普通系统提示", "TackShot is great")
print("without:", r2["choices"][0]["message"]["content"])
print("stats2:", urllib.request.urlopen("http://127.0.0.1:8899/stats", timeout=10).read().decode())
