import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import onnxruntime as ort

d = r"C:\Users\laiki\.dsh\workspace\tackshot\dl\models\pix2text-mfr-1.5"

# 渲染一张公式图
img = Image.new("RGB", (420, 120), "white")
dr = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("C:/Windows/Fonts/cambria.ttc", 44)
except Exception:
    font = ImageFont.load_default()
dr.text((14, 26), "x2 + y2 = r2", fill="black", font=font)
img.save(r"C:\Users\laiki\.dsh\workspace\tackshot\build\formula_ref.png")

enc = ort.InferenceSession(os.path.join(d,"encoder_model.onnx"), providers=["CPUExecutionProvider"])
dec = ort.InferenceSession(os.path.join(d,"decoder_model.onnx"), providers=["CPUExecutionProvider"])

x = np.asarray(img.resize((384,384), Image.BICUBIC), dtype=np.float32) / 255.0
x = (x - 0.5) / 0.5
x = np.transpose(x, (2,0,1))[None, ...]
hidden = enc.run(None, {"pixel_values": x})[0]
print("hidden", hidden.shape)

vocab = json.load(open(os.path.join(d,"tokenizer.json"), encoding="utf-8"))["model"]["vocab"]
id2tok = {v:k for k,v in vocab.items()}

ids = [1]
out = []
for step in range(300):
    logits = dec.run(None, {"input_ids": np.array([ids], dtype=np.int64),
                            "encoder_hidden_states": hidden})[0]
    nxt = int(np.argmax(logits[0, -1]))
    if nxt == 2: break
    ids.append(nxt)
    out.append(nxt)

text = "".join(id2tok.get(i, "") for i in out).replace("\u0120", " ")
print("tokens:", out[:40])
print("LATEX:", text)
open(r"C:\Users\laiki\.dsh\workspace\tackshot\build\formula_ref.txt","w",encoding="utf-8").write(text)
