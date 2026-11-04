import urllib.request, traceback
try:
    r = urllib.request.urlopen("http://127.0.0.1:8899/stats", timeout=5)
    print("OK", r.status, r.read().decode())
except Exception as e:
    print("ERR", type(e).__name__, e)
    try:
        print("body:", e.read().decode()[:300])
    except Exception:
        pass
