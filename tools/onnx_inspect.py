import sys, struct, json, os
from collections import defaultdict

def rd_varint(b, i):
    v = 0; s = 0
    while True:
        c = b[i]; i += 1
        v |= (c & 0x7f) << s; s += 7
        if not (c & 0x80): return v, i

def parse(b, depth=0):
    i = 0; out = []
    n = len(b)
    while i < n:
        key, i = rd_varint(b, i)
        f, wt = key >> 3, key & 7
        if wt == 0:
            v, i = rd_varint(b, i); out.append((f, 0, v))
        elif wt == 2:
            ln, i = rd_varint(b, i); out.append((f, 2, b[i:i+ln])); i += ln
        elif wt == 5:
            out.append((f, 5, b[i:i+4])); i += 4
        elif wt == 1:
            out.append((f, 1, b[i:i+8])); i += 8
        else:
            break   # 尾部可能有多余字节，忽略
    return out

def get(model, field):
    return [v for (f, t, v) in model if f == field]

def value_info(b):
    name = ""
    dims = []
    for f, t, v in parse(b):
        if f == 1 and t == 2: name = v.decode("utf-8", "replace")
        if f == 2 and t == 2:
            for f2, t2, v2 in parse(v):          # TypeProto
                if f2 == 1 and t2 == 2:          # tensor_type
                    for f3, t3, v3 in parse(v2):  # TypeProto.Tensor
                        if f3 == 2 and t3 == 2:   # shape
                            for f4, t4, v4 in parse(v3):
                                if f4 == 1 and t4 == 2:
                                    d = None
                                    for f5, t5, v5 in parse(v4):
                                        if f5 == 1: d = v5
                                        if f5 == 2: d = v5.decode("utf-8", "replace")
                                    dims.append(d)
    return name, dims

def inspect(path):
    b = open(path, "rb").read()
    m = parse(b)
    graph = None; opset = []
    for f, t, v in m:
        if f == 7 and t == 2: graph = v
        if f == 8 and t == 2:
            ver = None
            for f2, t2, v2 in parse(v):
                if f2 == 2: ver = v2
            opset.append(ver)
    if graph is None: return None
    g = parse(graph)
    ins = [value_info(v) for f, t, v in g if f == 11 and t == 2]
    outs = [value_info(v) for f, t, v in g if f == 12 and t == 2]
    nodes = 0; ops = defaultdict(int)
    for f, t, v in g:
        if f == 1 and t == 2:
            nodes += 1
            for f2, t2, v2 in parse(v):
                if f2 == 4 and t2 == 2: ops[v2.decode("utf-8", "replace")] += 1
    return {"file": os.path.basename(path), "size": len(b), "opset": opset,
            "inputs": ins, "outputs": outs, "nodes": nodes, "op_top": dict(sorted(ops.items(), key=lambda x: -x[1])[:6])}

root = r"C:\Users\laiki\.dsh\workspace\tackshot\models"
os.makedirs(root, exist_ok=True)
src = r"C:\Users\laiki\AppData\Local\Programs\PixPin\model"
KEY = b"wsK&56aeSk!Rn7Lb"
def dec(d):
    n = len(d); k = (KEY * (n // len(KEY) + 1))[:n]
    return (int.from_bytes(d, "big") ^ int.from_bytes(k, "big")).to_bytes(n, "big")

cands = []
for fn in sorted(os.listdir(src)):
    p = os.path.join(src, fn)
    if fn.endswith(".bin"):
        out = os.path.join(root, fn.replace(".bin", ".onnx"))
        if not os.path.exists(out):
            open(out, "wb").write(dec(open(p, "rb").read()))
        cands.append(out)
    elif fn.endswith(".onnx"):
        out = os.path.join(root, fn)
        if not os.path.exists(out):
            open(out, "wb").write(open(p, "rb").read())
        cands.append(out)

for c in cands:
    r = inspect(c)
    print(json.dumps(r, ensure_ascii=False))
