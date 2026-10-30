import argparse, json
from collections import Counter
from datetime import datetime, timedelta
import requests

ap = argparse.ArgumentParser()
ap.add_argument("--log", default="noise_log.jsonl")
ap.add_argument("--model", default="qwen3.5:0.8b")
ap.add_argument("--no-qwen", action="store_true", help="skip Qwen, only print facts")
args = ap.parse_args()

def t(dt):
    return dt.strftime("%-I:%M %p")

try:
    events = [json.loads(l) for l in open(args.log) if l.strip()]
except FileNotFoundError:
    events = []

if not events:
    print("Quiet night. No loud events were logged.")
    raise SystemExit

for e in events:
    e["start"] = datetime.strptime(e["date"] + " " + e["time"], "%Y-%m-%d %H:%M:%S")
    e["end"] = e["start"] + timedelta(seconds=e["seconds"])
events.sort(key=lambda e: e["start"])

counts = Counter(e["kind"] for e in events)
longest = max(events, key=lambda e: e["seconds"])
sirens = [e for e in events if e["kind"] == "siren"]
busiest_hour = Counter(e["start"].replace(minute=0, second=0) for e in events).most_common(1)[0]

gap, gap_from, gap_to = timedelta(0), None, None
for a, b in zip(events, events[1:]):
    if b["start"] - a["end"] > gap:
        gap, gap_from, gap_to = b["start"] - a["end"], a["end"], b["start"]

facts = [
    f"{len(events)} loud events between {t(events[0]['start'])} and {t(events[-1]['start'])}.",
    "By type: " + ", ".join(f"{n} {k}" for k, n in counts.most_common()) + ".",
    f"Longest event: {longest['kind']} at {t(longest['start'])}, {longest['seconds']} seconds.",
    f"Busiest hour: {t(busiest_hour[0])} with {busiest_hour[1]} events.",
]
if sirens:
    s = max(sirens, key=lambda e: e["seconds"])
    facts.append(f"Longest siren: {t(s['start'])}, {s['seconds']} seconds.")
if gap_from:
    facts.append(f"Quietest stretch: {t(gap_from)} to {t(gap_to)}.")

print("FACTS")
for f in facts:
    print(" -", f)

print("\nTIMELINE  (S siren, C construction, V voices, T traffic, D dog, M music, I inside, O other)")
letter = {"siren": "S", "construction": "C", "voices": "V", "traffic": "T", "dog": "D", "music": "M", "inside": "I"}
hour = events[0]["start"].replace(minute=0, second=0)
while hour <= events[-1]["start"]:
    marks = "".join(letter.get(e["kind"], "O") for e in events if hour <= e["start"] < hour + timedelta(hours=1))
    print(f"  {hour.strftime('%-I %p'):>6}  {marks}")
    hour += timedelta(hours=1)

if args.no_qwen:
    raise SystemExit

kinds = ", ".join(f"{n} {k}" for k, n in counts.most_common())
report = f"Last night had {len(events)} loud events: {kinds}."
if sirens:
    s = max(sirens, key=lambda e: e["seconds"])
    report += f" The longest siren was at {t(s['start'])} and lasted {s['seconds']} seconds."
else:
    report += f" The longest sound was {longest['kind']} at {t(longest['start'])}."
if gap_from:
    report += f" The quietest stretch was {t(gap_from)} to {t(gap_to)}."

print("\nMORNING REPORT")
print(report)

choices = "\n".join(
    f"{i}: {e['kind']} at {t(e['start'])}, {e['seconds']} seconds, {e['above_background_db']} dB above background"
    for i, e in enumerate(events)
)
prompt = (
    "These loud sounds happened outside a bedroom window last night:\n"
    + choices
    + '\n\nWhich ONE was most likely to wake someone up? Louder and longer sounds are more likely. '
    'Answer as JSON: {"event": <number>}'
)
pick = None
try:
    r = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": args.model,
            "messages": [{"role": "user", "content": prompt}],
            "think": False,
            "stream": False,
            "format": "json",
            "options": {"num_predict": 20},
        },
        timeout=600,
    )
    pick = int(json.loads(r.json()["message"]["content"])["event"])
    if not 0 <= pick < len(events):
        pick = None
except Exception:
    pick = None

source = "Qwen"
if pick is None:
    pick = max(range(len(events)), key=lambda i: events[i]["above_background_db"])
    source = "loudest event (Qwen answer was not usable)"
w = events[pick]
print(f"Most likely woke you: {w['kind']} at {t(w['start'])}, {w['seconds']} seconds, "
      f"{w['above_background_db']} dB above background.  [picked by {source}]")

# ---- chart ----
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

colors = {"siren": "#E24B4A", "construction": "#BA7517", "voices": "#888780", "traffic": "#378ADD",
          "dog": "#1D9E75", "music": "#7F77DD", "inside": "#D4537E", "other": "#B4B2A9"}

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), gridspec_kw={"height_ratios": [2, 1]})

min_width = timedelta(minutes=6)
for e in events:
    width = max(timedelta(seconds=e["seconds"]), min_width)
    ax1.bar(e["start"], e["above_background_db"], width=width, align="edge",
            color=colors.get(e["kind"], "#B4B2A9"))
ax1.set_title("Last night's noise")
ax1.set_ylabel("dB above background")
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%-I %p"))
ax1.xaxis.set_major_locator(mdates.HourLocator())
ax1.spines[["top", "right"]].set_visible(False)

kinds_sorted = [k for k, _ in counts.most_common()][::-1]
ax2.barh(kinds_sorted, [counts[k] for k in kinds_sorted], color=[colors.get(k, "#B4B2A9") for k in kinds_sorted])
ax2.set_xlabel("Number of events")
ax2.xaxis.get_major_locator().set_params(integer=True)
ax2.spines[["top", "right"]].set_visible(False)

fig.tight_layout()
fig.savefig("noise_report.png", dpi=120)
print("Chart saved to noise_report.png")
