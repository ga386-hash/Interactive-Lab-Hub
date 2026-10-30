import argparse, csv, json, subprocess
from collections import Counter
from datetime import datetime
import numpy as np
from ai_edge_litert.interpreter import Interpreter

ap = argparse.ArgumentParser()
ap.add_argument("--device", default="plughw:3,0")
ap.add_argument("--margin", type=float, default=8, help="dB above background to count as loud")
ap.add_argument("--gap", type=int, default=4, help="quiet seconds that end an event")
ap.add_argument("--switch", type=int, default=2, help="seconds of a new sound type that start a new event")
ap.add_argument("--min", type=int, default=2, help="shortest event to keep, in seconds")
ap.add_argument("--log", default="noise_log.jsonl")
args = ap.parse_args()

GROUPS = [
    ("siren", ["siren", "police car", "ambulance", "fire engine", "fire truck", "emergency vehicle", "civil defense"]),
    ("construction", ["jackhammer", "drill", "hammer", "power tool", "saw", "sanding", "filing", "construction"]),
    ("voices", ["speech", "shout", "yell", "laughter", "conversation", "crowd", "babble", "chatter", "scream", "children"]),
    ("traffic", ["vehicle", "car", "truck", "bus", "motorcycle", "horn", "honk", "traffic", "engine", "skidding", "motor"]),
    ("dog", ["dog", "bark", "howl", "bow-wow"]),
    ("music", ["music", "song", "singing", "guitar", "drum", "piano"]),
    ("inside", ["hands", "clap", "knock", "door", "footsteps", "tap", "typing", "slam"]),
]

def group(name):
    n = name.lower()
    if n == "silence":
        return "quiet"
    for g, keys in GROUPS:
        if any(k in n for k in keys):
            return g
    return "other"

labels = [r["display_name"] for r in csv.DictReader(open("yamnet_class_map.csv"))]
cats = [group(l) for l in labels]
model = Interpreter(model_path="yamnet.tflite")
model.allocate_tensors()
inp = model.get_input_details()[0]
out = model.get_output_details()[0]

N = 15600  # about 1 second at 16 kHz
proc = subprocess.Popen(
    ["arecord", "-D", args.device, "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "raw", "-q"],
    stdout=subprocess.PIPE,
)

def read_chunk():
    data = proc.stdout.read(N * 2)
    if len(data) < N * 2:
        return None
    return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768

def level_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)

def classify(x):
    model.set_tensor(inp["index"], x.reshape(inp["shape"]))
    model.invoke()
    scores = model.get_tensor(out["index"]).reshape(-1)
    top = scores.argsort()[-5:][::-1]
    totals = Counter()
    for j in top:
        totals[cats[j]] += float(scores[j])
    best = [c for c, _ in totals.most_common() if c not in ("other", "quiet")]
    return (best[0] if best else "other"), labels[top[0]]

def new_event(t):
    return {"start": t, "end": t, "cats": [], "peak": -999, "labels": Counter()}

def add(ev, t, cat, label, lvl):
    ev["cats"].append(cat)
    ev["labels"][label] += 1
    ev["peak"] = max(ev["peak"], lvl)
    ev["end"] = t

def kind_of(ev):
    return Counter(ev["cats"]).most_common(1)[0][0]

def save(ev):
    seconds = round((ev["end"] - ev["start"]).total_seconds()) + 1
    if seconds < args.min:
        return
    rec = {
        "date": ev["start"].strftime("%Y-%m-%d"),
        "time": ev["start"].strftime("%H:%M:%S"),
        "kind": kind_of(ev),
        "seconds": seconds,
        "peak_db": round(ev["peak"], 1),
        "above_background_db": round(ev["peak"] - background, 1),
        "top_label": ev["labels"].most_common(1)[0][0],
    }
    with open(args.log, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"SAVED  {rec['time']}  {rec['kind']}  {seconds} s  (+{rec['above_background_db']} dB, {rec['top_label']})")

print("Calibrating for 5 seconds, keep it quiet...")
levels = [level_db(read_chunk()) for _ in range(5)]
background = float(np.median(levels))
threshold = background + args.margin
print(f"Background {background:.1f} dB, loud means above {threshold:.1f} dB. Listening. Ctrl-C to stop.")

event, quiet, pending = None, 0, []
try:
    while True:
        x = read_chunk()
        if x is None:
            break
        lvl = level_db(x)
        now = datetime.now()
        if lvl < threshold:
            if event is not None:
                quiet += 1
                if quiet >= args.gap:
                    for p in pending:
                        add(event, *p)
                    save(event)
                    event, quiet, pending = None, 0, []
            continue

        cat, label = classify(x)
        print(f"  {now:%H:%M:%S}  {lvl:6.1f} dB  {cat}")
        quiet = 0
        if event is None:
            event = new_event(now)
            add(event, now, cat, label, lvl)
        elif cat == kind_of(event):
            for p in pending:
                add(event, *p)
            pending = []
            add(event, now, cat, label, lvl)
        else:
            pending.append((now, cat, label, lvl))
            last = pending[-args.switch:]
            if len(last) >= args.switch and all(p[1] == last[-1][1] for p in last):
                for p in pending[:-args.switch]:
                    add(event, *p)
                save(event)
                event = new_event(last[0][0])
                for p in last:
                    add(event, *p)
                pending = []
except KeyboardInterrupt:
    pass
finally:
    if event is not None:
        for p in pending:
            add(event, *p)
        save(event)
    proc.terminate()
    print("Stopped.")
