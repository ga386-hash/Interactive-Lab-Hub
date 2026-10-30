import os, signal, subprocess, textwrap, time
from datetime import datetime
import cv2
import mediapipe as mp
import board, digitalio
import pitft

btns = []
for pin in (board.D23, board.D24):
    b = digitalio.DigitalInOut(pin)
    b.switch_to_input(pull=digitalio.Pull.UP)
    btns.append(b)

def pressed():
    return any(not b.value for b in btns)

def wait_release():
    while pressed():
        time.sleep(0.05)

def wait_for_peace(hold=1.5):
    pitft.show_text(["Show a peace sign", "to start the night"], size=16)
    cap = cv2.VideoCapture(0)
    hands = mp.solutions.hands.Hands(max_num_hands=1, min_detection_confidence=0.6)
    since, showing = None, False
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                continue
            res = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            peace = False
            if res.multi_hand_landmarks:
                lm = res.multi_hand_landmarks[0].landmark
                up = lambda tip, pip: lm[tip].y < lm[pip].y
                peace = up(8, 6) and up(12, 10) and not up(16, 14) and not up(20, 18)
            if peace:
                if since is None:
                    since = time.time()
                if not showing:
                    pitft.show_text(["Peace sign seen", "hold it..."], color="#7F77DD", size=16)
                    showing = True
                if time.time() - since >= hold:
                    return
            else:
                if showing:
                    pitft.show_text(["Show a peace sign", "to start the night"], size=16)
                    showing = False
                since = None
    finally:
        cap.release()
        hands.close()

def wrap(text, width=22):
    return textwrap.wrap(text, width)[:6]

# ---- bedtime ----
wait_for_peace()

if os.path.exists("noise_log.jsonl"):
    os.rename("noise_log.jsonl", f"noise_log_{datetime.now():%Y-%m-%d_%H%M}.jsonl")

pitft.show_text(["Listening.", "Goodnight."], color="#7F77DD", size=24)
time.sleep(3)
pitft.light(False)

# ---- overnight ----
logger = subprocess.Popen(["python", "noise_logger.py"])
try:
    while logger.poll() is None and not pressed():
        time.sleep(0.2)
except KeyboardInterrupt:
    pass
if logger.poll() is None:
    logger.send_signal(signal.SIGINT)
try:
    logger.wait(timeout=10)
except subprocess.TimeoutExpired:
    logger.kill()

# ---- morning ----
pitft.light(True)
pitft.show_text(["Good morning!", "Making your", "report..."], color="#EF9F27", size=18)
out = subprocess.run(["python", "noise_morning.py"], capture_output=True, text=True).stdout
print(out)

lines = out.splitlines()
if "Quiet night" in out:
    pages = [["Quiet night.", "No loud events", "were logged."]]
else:
    report = next((lines[i + 1] for i, l in enumerate(lines) if l.strip() == "MORNING REPORT"), "")
    woke = next((l for l in lines if l.startswith("Most likely woke you")), "")
    woke = woke.split("  [")[0]
    pages = [wrap(report), wrap(woke), "chart"]

wait_release()
i = 0
try:
    while True:
        page = pages[i % len(pages)]
        if page == "chart":
            pitft.show_image("noise_report.png")
        else:
            pitft.show_text(page, size=14)
        while not pressed():
            time.sleep(0.05)
        wait_release()
        i += 1
except KeyboardInterrupt:
    pitft.show_text(["Have a good day!"], size=18)
