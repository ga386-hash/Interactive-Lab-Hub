import csv, wave, sys
import numpy as np
from ai_edge_litert.interpreter import Interpreter

labels = [r["display_name"] for r in csv.DictReader(open("yamnet_class_map.csv"))]
model = Interpreter(model_path="yamnet.tflite")
model.allocate_tensors()
inp = model.get_input_details()[0]
out = model.get_output_details()[0]

w = wave.open(sys.argv[1] if len(sys.argv) > 1 else "test.wav")
audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
N = 15600  # about 1 second of audio

for i in range(0, len(audio) - N + 1, N):
    chunk = audio[i:i + N].reshape(inp["shape"])
    model.set_tensor(inp["index"], chunk)
    model.invoke()
    scores = model.get_tensor(out["index"]).reshape(-1)
    top = scores.argsort()[-3:][::-1]
    print(f"{i/16000:5.1f}s  " + ", ".join(f"{labels[j]} {scores[j]:.2f}" for j in top))
