import json, os
import onnxruntime as ort

d = r"C:\Users\laiki\.dsh\workspace\tackshot\dl\models\pix2text-mfr-1.5"
for f in ["preprocessor_config.json","generation_config.json","config.json"]:
    p = os.path.join(d,f)
    if os.path.exists(p):
        j = json.load(open(p, encoding="utf-8"))
        print("==",f,"==")
        print(json.dumps(j, ensure_ascii=False)[:800])

sess = ort.InferenceSession(os.path.join(d,"encoder_model.onnx"), providers=["CPUExecutionProvider"])
print("\nencoder inputs:", [(i.name, i.shape, i.type) for i in sess.get_inputs()])
print("encoder outputs:", [(o.name, o.shape, o.type) for o in sess.get_outputs()])

dec = ort.InferenceSession(os.path.join(d,"decoder_model.onnx"), providers=["CPUExecutionProvider"])
print("\ndecoder inputs:", [(i.name, i.shape) for i in dec.get_inputs()])
print("decoder outputs:", [(o.name, o.shape) for o in dec.get_outputs()][:6])

tok = json.load(open(os.path.join(d,"tokenizer.json"), encoding="utf-8"))
print("\ntokenizer model:", tok["model"]["type"], "vocab:", len(tok["model"]["vocab"]))
print("added tokens:", tok.get("added_tokens", [])[:5])
print("post_processor:", json.dumps(tok.get("post_processor", {}), ensure_ascii=False)[:300])
