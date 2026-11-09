#!/usr/bin/env python3
"""NEON RACE - Lab 6 distributed reaction game.

Run on the course 240x135 Mini PiTFT, APDS-9960 and optional USB webcam.
Host: python neon_race.py --host --name pi1
Others: python neon_race.py --name pi2  (and --name pi3)
Solo hardware test: python neon_race.py --practice
Read NEON_RACE.md for setup, MQTT protocol, and remaining lab documentation.

Created with Stephen and Codex. Uses the course screen wiring and MQTT broker,
Adafruit drivers, Pillow, Paho MQTT, and Google's MediaPipe Gesture Recognizer.
"""
"""Pure state machine for NEON RACE. No network or hardware access."""
import math
import random
import re
import uuid


RACE_TASKS = {
    "red": "SHOW RED", "green": "SHOW GREEN", "blue": "SHOW BLUE",
    "peace": "PEACE SIGN", "palm": "OPEN PALM", "fist": "MAKE A FIST",
    "thumbs_up": "THUMBS UP", "near": "HAND CLOSE",
}


class RaceHost:
    """Authoritative scorekeeper; all ``now`` arguments use time.monotonic().

    Publish every (kind, payload) returned by drain() to the team's MQTT topic.
    The host waits for the complete response window, then compares client-local
    elapsed times. This avoids comparing unsynchronised wall clocks, but does
    not eliminate sensor/frame latency or different GO-message arrival times.
    This is a trusted classroom game, not an anti-cheat system.
    """
    def __init__(self, min_players=3, rounds=5, seed=None, countdown=3.0,
                 duration=12.0, grace=1.5, result_time=4.0, max_players=8):
        if min_players < 1 or rounds < 1:
            raise ValueError("Need at least one player and one round")
        self.min_players = min_players
        self.max_players = max_players
        self.rounds = rounds
        self.countdown = countdown
        self.duration = duration
        self.grace = grace
        self.result_time = result_time
        self.rng = random.Random(seed)
        self.players = {}
        self.roster = {}
        self.scores = {}
        self.outbox = []
        self.session = uuid.uuid4().hex
        self.round = 0
        self.phase = "lobby"
        self.task = None
        self.tasks = []
        self.ready = set()
        self.answers = {}
        self.winners = []
        self.champions = []
        self.message = "Waiting for players"
        self.go_at = 0.0
        self.deadline = 0.0
        self.phase_until = 0.0
        self.last_state = -100.0

    def snapshot(self):
        return {
            "session": self.session, "round": self.round,
            "rounds": self.rounds, "phase": self.phase,
            "task": self.task,
            "label": RACE_TASKS.get(self.task, "NEON RACE"),
            "players": sorted(self.players), "roster": sorted(self.roster),
            "ready": sorted(self.ready), "scores": dict(self.scores),
            "answers": dict(self.answers), "winners": list(self.winners),
            "champions": list(self.champions), "message": self.message,
            "min_players": self.min_players,
            "duration": self.duration, "delay": self.countdown,
        }

    def drain(self):
        pending, self.outbox = self.outbox, []
        return pending

    def _emit(self, kind):
        self.outbox.append((kind, self.snapshot()))

    def _abort(self, message):
        self.phase = "lobby"
        self.message = message
        self.roster = {}
        self.ready = set()
        self.answers = {}
        self.task = None
        self._emit("state")

    def handle(self, kind, payload, now):
        if not isinstance(payload, dict):
            return False
        player, boot = payload.get("player"), payload.get("boot")
        if not isinstance(player, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,24}", player):
            return False
        if not isinstance(boot, str) or not 1 <= len(boot) <= 80:
            return False
        if kind == "hello":
            if payload.get("online") is False:
                item = self.players.get(player)
                if item is None or item["boot"] != boot:
                    return False
                del self.players[player]
                if player in self.roster and self.phase not in ("lobby", "finished"):
                    self._abort("Lost Pi: " + player + "; restart match")
                return True
            caps = payload.get("caps")
            if not isinstance(caps, list) or len(caps) > 32:
                return False
            if any(not isinstance(c, str) for c in caps):
                return False
            supported = set(caps) & set(RACE_TASKS)
            # Reboots or duplicate names must not inherit an old player's score.
            if player in self.roster and self.roster[player] != boot:
                self._abort("Player restarted or duplicate name: " + player)
            self.players[player] = {"boot": boot, "caps": supported, "seen": now}
            return True
        if (payload.get("session") != self.session or
                payload.get("round") != self.round or
                self.roster.get(player) != boot):
            return False
        if kind == "ready" and self.phase == "arming":
            self.ready.add(player)
            if self.ready == set(self.roster):
                self.phase = "countdown"
                self.go_at = now + self.countdown
                self.deadline = self.go_at + self.duration + self.grace
                self.message = "Get ready"
                self._emit("go")
            return True
        if kind != "done" or self.phase not in ("countdown", "racing"):
            return False
        # A sender cannot finish before GO or after the receipt grace period.
        if now < self.go_at or now > self.deadline or player in self.answers:
            return False
        elapsed = payload.get("elapsed")
        if (isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or
                not math.isfinite(elapsed) or not 0 <= elapsed <= self.duration or
                payload.get("task") != self.task):
            return False
        self.answers[player] = float(elapsed)
        self._emit("state")
        return True

    def start(self, now):
        if self.phase not in ("lobby", "finished"):
            return False
        self._expire(now)
        if len(self.players) < self.min_players:
            self.message = "Need %d Pis; %d joined" % (self.min_players, len(self.players))
            self._emit("state")
            return False
        if len(self.players) > self.max_players:
            self.message = "Maximum %d players; use your own team name" % self.max_players
            self._emit("state")
            return False
        common = set(RACE_TASKS)
        for item in self.players.values():
            common &= item["caps"]
        if not common:
            self.message = "No shared sensor challenges; check each Pi"
            self._emit("state")
            return False
        self.session = uuid.uuid4().hex
        self.roster = {name: item["boot"] for name, item in self.players.items()}
        self.scores = {name: 0 for name in self.roster}
        self.tasks = sorted(common)
        self.round = 0
        self.task = None
        self.champions = []
        self._prepare(now)
        return True

    def _prepare(self, now):
        previous = self.task
        choices = [t for t in self.tasks if t != previous] or self.tasks
        if self.round == 0 and "peace" in choices:
            choices = ["peace"]
        elif self.round == 1:
            colors = [t for t in choices if t in ("red", "green", "blue")]
            choices = colors or choices
        self.task = self.rng.choice(choices)
        self.round += 1
        self.phase = "arming"
        self.ready = set()
        self.answers = {}
        self.winners = []
        self.phase_until = now + 15.0
        self.message = "Waiting for every Pi to be ready"
        self._emit("prepare")

    def _score(self, now):
        self.winners = []
        if self.answers:
            best = min(self.answers.values())
            # Below one low-rate camera frame is too close to call reliably.
            self.winners = sorted(p for p, elapsed in self.answers.items()
                                  if elapsed - best <= 0.08000001)
            for player in self.winners:
                self.scores[player] += 1
            self.message = ("TIE: " if len(self.winners) > 1 else "WIN: ") + ", ".join(self.winners)
        else:
            self.message = "TIME UP - no finish"
        self.phase = "result"
        self.phase_until = now + self.result_time
        self._emit("result")

    def _expire(self, now):
        for player in list(self.players):
            if now - self.players[player]["seen"] > 15.0:
                del self.players[player]

    def tick(self, now):
        self._expire(now)
        if self.phase in ("arming", "countdown", "racing", "result"):
            missing = set(self.roster) - set(self.players)
            if missing:
                self._abort("Lost Pi: " + ", ".join(sorted(missing)) + "; restart match")
                return
        if self.phase == "arming" and now >= self.phase_until:
            self._abort("A Pi did not get ready; restart match")
        elif self.phase == "countdown" and now >= self.go_at:
            self.phase = "racing"
            self.message = "GO!"
            self._emit("state")
        if self.phase == "racing" and now >= self.deadline:
            self._score(now)
        elif self.phase == "result" and now >= self.phase_until:
            if self.round >= self.rounds:
                best = max(self.scores.values(), default=0)
                self.champions = sorted(p for p, s in self.scores.items() if s == best) if best else []
                self.phase = "finished"
                if not self.champions:
                    self.message = "NO WINNER - try again"
                elif len(self.champions) > 1:
                    self.message = "SHARED CHAMPIONS: " + ", ".join(self.champions)
                else:
                    self.message = "CHAMPION: " + self.champions[0]
                self._emit("state")
            else:
                self._prepare(now)
        if now - self.last_state >= 1.0:
            self.last_state = now
            self._emit("prepare" if self.phase == "arming" else "state")


"""Neon Race hardware: camera inference off the drawing thread, no desktop needed."""
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import urllib.request


def classify_rgb(red, green, blue, clear=None):
    """Conservative dominant-channel classification, not calibrated colorimetry."""
    values = [max(0, float(red)), max(0, float(green)), max(0, float(blue))]
    if clear is not None and (clear < 12 or clear >= 65000):
        return None
    peak = max(values)
    if peak < 8:
        return None
    ordered = sorted(values, reverse=True)
    # White/grey and ambiguous mixed colors should never count as an answer.
    if peak < ordered[1] * 1.35 or peak / max(sum(values), 1) < .43:
        return None
    return ("red", "green", "blue")[values.index(peak)]


def _neon_model_path(model_path=None):
    """Fetch Google's versioned gesture bundle once, never into the repository."""
    if model_path is not None:
        path = Path(model_path).expanduser()
        if not path.is_file():
            raise FileNotFoundError("Gesture model not found: " + str(path))
        return path
    path = Path.home() / ".cache" / "neon-race" / "gesture_recognizer-v1.task"
    if path.is_file() and path.stat().st_size > 100000:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    url = ("https://storage.googleapis.com/mediapipe-models/gesture_recognizer/"
           "gesture_recognizer/float16/1/gesture_recognizer.task")
    print("Camera: downloading Google's gesture model once...", flush=True)
    tmp = None
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
                tmp = Path(output.name)
                total = 0
                deadline = time.monotonic() + 90
                while True:
                    data = response.read(65536)
                    if not data:
                        break
                    total += len(data)
                    if total > 32 * 1024 * 1024 or time.monotonic() > deadline:
                        raise RuntimeError("Gesture model download exceeded its limit")
                    output.write(data)
        if total < 100000:
            raise RuntimeError("Downloaded gesture model is incomplete")
        os.replace(tmp, path)
        return path
    finally:
        if tmp is not None and tmp.exists():
            tmp.unlink()


class SensorInputs:
    """Background camera + APDS-9960 input; images never leave this process."""
    GESTURES = {"Victory": "peace", "Open_Palm": "palm",
                "Closed_Fist": "fist", "Thumb_Up": "thumbs_up"}
    COLOR_TASKS = {"red", "green", "blue", "near"}

    def __init__(self, camera=0, no_camera=False, no_sensor=False, model_path=None):
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._threads = []
        self._caps = set()
        self._errors = {}
        self._state = dict(task=None, color=None, gesture=None, rgb=(0, 0, 0),
                           near=False, updated=0.0, gesture_updated=0.0,
                           color_updated=0.0, proximity=0, error="",
                           camera_ready=False, sensor_ready=False,
                           camera_status="off" if no_camera else "starting",
                           sensor_status="off" if no_sensor else "starting")
        if not no_sensor:
            self._launch(self._sensor_loop, "neon-sensor")
        if not no_camera:
            self._launch(lambda: self._camera_loop(camera, model_path), "neon-camera")

    def _launch(self, fn, name):
        thread = threading.Thread(target=fn, name=name, daemon=True)
        self._threads.append(thread)
        thread.start()

    @property
    def capabilities(self):
        with self._lock:
            return set(self._caps)

    def _error(self, stream, exc):
        text = stream + ": " + str(exc)
        print(text, flush=True)
        with self._lock:
            self._errors[stream] = text
            self._state[stream + "_status"] = "error"
            self._state[stream + "_ready"] = False
            if stream == "camera":
                self._caps.difference_update(self.GESTURES.values())
                self._state.update(gesture=None, gesture_updated=0.0)
            else:
                self._caps.difference_update(self.COLOR_TASKS)
                self._state.update(color=None, near=False, color_updated=0.0)

    def poll(self):
        with self._lock:
            result = dict(self._state)
            result["error"] = " | ".join(self._errors.values())
        # A stalled camera/USB read must not leave a winning pose stuck forever.
        now = time.monotonic()
        if now - result["gesture_updated"] > 1.0:
            result["gesture"] = None
        if now - result["color_updated"] > 1.0:
            result.update(color=None, near=False)
        result["task"] = result["gesture"] or result["color"] or (
            "near" if result["near"] else None)
        return result

    def _sensor_loop(self):
        i2c = sensor = None
        try:
            import board
            from adafruit_apds9960.apds9960 import APDS9960
            i2c = board.I2C()
            sensor = APDS9960(i2c)
            sensor.color_gain = 1  # 4x; the driver uses a 0..3 index.
            sensor.color_integration_time = 18  # 50 ms (units are 2.78 ms).
            sensor.enable_color = True
            sensor.enable_proximity = True
            while not self._stop.is_set():
                if sensor.color_data_ready:
                    r, g, b, clear = sensor.color_data
                    proximity = sensor.proximity
                    # Same blue correction used by the class's pixel demo.
                    corrected = (r * 1.2, g * 1.2, b * 1.7)
                    color = classify_rgb(*corrected, clear=clear)
                    peak = max(corrected)
                    rgb = tuple(int(min(255, v * 255 / peak)) if peak else 0
                                for v in corrected)
                    now = time.monotonic()
                    with self._lock:
                        self._state.update(color=color, rgb=rgb,
                                           near=proximity >= 100,
                                           proximity=proximity,
                                           updated=now, color_updated=now,
                                           sensor_ready=True, sensor_status="ready")
                        self._caps.update(self.COLOR_TASKS)
                self._stop.wait(.03)
        except Exception as exc:
            self._error("sensor", exc)
        finally:
            if sensor is not None:
                try:
                    sensor.enable_color = False
                    sensor.enable_proximity = False
                except Exception:
                    pass
            if i2c is not None:
                try:
                    i2c.deinit()
                except Exception:
                    pass

    def _camera_loop(self, camera, model_path):
        cap = recognizer = None
        try:
            import cv2
            import mediapipe as mp
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision
            model = _neon_model_path(model_path)
            if self._stop.is_set():
                return
            options = vision.GestureRecognizerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=str(model)),
                running_mode=vision.RunningMode.VIDEO, num_hands=1,
                min_hand_detection_confidence=.6,
                min_hand_presence_confidence=.6, min_tracking_confidence=.6)
            recognizer = vision.GestureRecognizer.create_from_options(options)
            cap = cv2.VideoCapture(camera)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            cap.set(cv2.CAP_PROP_FPS, 15)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not cap.isOpened():
                raise RuntimeError("USB webcam did not open; check --camera index")
            last_ms = -1
            failures = 0
            while not self._stop.is_set():
                start = time.monotonic()
                ok, frame = cap.read()
                captured = time.monotonic()
                if not ok or frame is None:
                    failures += 1
                    if failures >= 5:
                        raise RuntimeError("USB webcam stopped returning frames")
                    self._stop.wait(.1)
                    continue
                failures = 0
                frame = cv2.resize(frame, (320, 240))
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                stamp = max(last_ms + 1, int(captured * 1000))
                last_ms = stamp
                result = recognizer.recognize_for_video(
                    mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), stamp)
                gesture = None
                if result.gestures and result.gestures[0]:
                    category = result.gestures[0][0]
                    if category.score >= .65:
                        gesture = self.GESTURES.get(category.category_name)
                with self._lock:
                    self._state.update(gesture=gesture, gesture_updated=captured,
                                       updated=time.monotonic(), camera_ready=True,
                                       camera_status="ready")
                    self._caps.update(self.GESTURES.values())
                self._stop.wait(max(0, 1 / 12 - (time.monotonic() - start)))
        except Exception as exc:
            self._error("camera", exc)
        finally:
            if cap is not None:
                cap.release()
            if recognizer is not None:
                recognizer.close()

    def close(self):
        self._stop.set()
        for thread in self._threads:
            thread.join(timeout=1.5)


class PiScreen:
    """Course Mini PiTFT, with GPIO5 CS and debounced top/bottom button edges."""
    def __init__(self):
        self._pins = []
        self._spi = None
        self._last = [False, False]
        self._changed = [0.0, 0.0]
        self._stable = [False, False]
        service = subprocess.run(["systemctl", "is-active", "--quiet", "piscreen.service"],
                                 capture_output=True, timeout=3)
        if service.returncode == 0:
            raise RuntimeError("Run sudo systemctl stop piscreen.service first. "
                               "Its button handler can shut down or reboot the Pi.")
        try:
            import board
            import digitalio
            from adafruit_rgb_display import st7789
            def pin(number):
                value = digitalio.DigitalInOut(number)
                self._pins.append(value)
                return value
            cs, dc = pin(board.D5), pin(board.D25)
            self._light = pin(board.D22)
            self._light.switch_to_output(value=True)
            self._buttons = [pin(board.D23), pin(board.D24)]
            for button in self._buttons:
                button.switch_to_input(pull=digitalio.Pull.UP)
            self._spi = board.SPI()
            self._display = st7789.ST7789(
                self._spi, cs=cs, dc=dc, rst=None, baudrate=24000000,
                width=135, height=240, x_offset=53, y_offset=40, rotation=90)
        except Exception:
            self.close()
            raise

    def draw(self, image):
        self._display.image(image)

    def buttons(self):
        now = time.monotonic()
        edges = [False, False]
        for i, button in enumerate(self._buttons):
            pressed = not button.value
            if pressed != self._last[i]:
                self._last[i], self._changed[i] = pressed, now
            if now - self._changed[i] >= .04 and pressed != self._stable[i]:
                self._stable[i] = pressed
                edges[i] = pressed
        return tuple(edges)

    def close(self):
        if hasattr(self, "_light"):
            try:
                self._light.value = False
            except Exception:
                pass
        for pin in reversed(self._pins):
            try:
                pin.deinit()
            except Exception:
                pass
        self._pins = []
        if self._spi is not None:
            try:
                self._spi.deinit()
            except Exception:
                pass
            self._spi = None


"""Animated 240 x 135 arcade graphics. Drawing only; no GPIO or camera access."""
import math as _nr_math
import random as _nr_random
from PIL import Image as _NRImage, ImageDraw as _NRDraw, ImageFont as _NRFont


class NeonRenderer:
    """Render one frame from the game's plain dictionary view model.

    Animation uses the caller's monotonic clock and never blocks the game loop.
    Camera frames are never displayed or stored by this renderer.
    """

    COLORS = [(57, 229, 255), (247, 70, 203), (184, 255, 64), (152, 111, 255)]
    TASKS = {
        "peace": ("PEACE", "SIGN", (57, 229, 255)),
        "open": ("OPEN", "PALM", (184, 255, 64)),
        "fist": ("MAKE A", "FIST", (247, 70, 203)),
        "thumbs_up": ("THUMBS", "UP", (255, 196, 65)),
        "point": ("POINT", "UP", (152, 111, 255)),
        "red": ("SHOW", "RED", (255, 82, 107)),
        "blue": ("SHOW", "BLUE", (57, 174, 255)),
        "green": ("SHOW", "GREEN", (121, 255, 91)),
        "near": ("HAND", "CLOSE", (255, 196, 65)),
    }

    def __init__(self):
        self.fonts = {}
        self.font_path = None
        for path in (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ):
            try:
                _NRFont.truetype(path, 14)
                self.font_path = path
                break
            except OSError:
                continue
        rng = _nr_random.Random(42)
        self.particles = [(rng.random(), rng.random(), rng.random(), rng.randrange(4))
                          for _ in range(34)]
        self.base = _NRImage.new("RGB", (240, 135))
        d = _NRDraw.Draw(self.base)
        for y in range(135):
            d.line((0, y, 239, y), fill=(7 + y // 20, 9, 23 + y // 9))

    def _font(self, size):
        if size not in self.fonts:
            if self.font_path:
                self.fonts[size] = _NRFont.truetype(self.font_path, size)
            else:
                try:
                    self.fonts[size] = _NRFont.load_default(size=size)
                except TypeError:
                    self.fonts[size] = _NRFont.load_default()
        return self.fonts[size]

    def _text(self, d, xy, text, size=12, color=(245, 249, 255), width=None,
              center=False):
        text = str(text)
        while width and d.textlength(text, font=self._font(size)) > width and size > 9:
            size -= 1
        if width and d.textlength(text, font=self._font(size)) > width:
            while text and d.textlength(text + "..", font=self._font(size)) > width:
                text = text[:-1]
            text += ".."
        x, y = xy
        if center:
            x -= d.textlength(text, font=self._font(size)) / 2
        d.text((x, y), text, font=self._font(size), fill=color, stroke_width=0)

    def _background(self, d, t, accent, intense=False):
        # Moving perspective grid: 100 short lines per frame, no blur or arrays.
        horizon = 89
        dim = tuple(max(12, v // 6) for v in accent)
        for x in range(-240, 481, 60):
            d.line((120, horizon, x + 12 * _nr_math.sin(t * .5), 135), fill=dim)
        for i in range(6):
            z = ((i / 6 + t * .13) % 1) ** 2
            y = horizon + int(z * 47)
            d.line((0, y, 239, y), fill=dim)
        for i in range(3):
            pts = [(x, 35 + i * 14 + 8 * _nr_math.sin(x * .035 + t * .8 + i))
                   for x in range(0, 241, 8)]
            d.line(pts, fill=(19 + i * 3, 19, 43 + i * 9), width=1)
        for u, v, speed, col in self.particles[:18 if not intense else 34]:
            x = int((u * 240 + t * (7 + speed * 15)) % 240)
            y = int((v * 135 + t * (10 if intense else 2)) % 135)
            c = self.COLORS[col]
            c = tuple(n // 3 for n in c) if not intense else c
            d.rectangle((x, y, x + (3 if intense else 1), y + (4 if intense else 1)), fill=c)

    def _header(self, d, view, accent):
        connected = view.get("connected", True)
        label = "PRACTICE" if view.get("practice") else "NEON / RACE"
        self._text(d, (10, 6), label, 10, accent)
        r = int(view.get("round", 0))
        if r:
            d.rectangle((174, 4, 239, 19), fill=(8, 10, 25))
            self._text(d, (179, 6), "%02d / %02d" % (r, view.get("total_rounds", 5)), 10)
        else:
            d.ellipse((217, 9, 222, 14), fill=(125, 255, 153) if connected else (255, 104, 104))
        d.line((10, 23, 229, 23), fill=tuple(v // 4 for v in accent))

    def _hand(self, d, cx, cy, task, color, t):
        # A hand assembled from rounded fingers, with a thick dark outline.
        x, y = cx - 21, cy - 7
        dark = (12, 15, 36)
        if task == "thumbs_up":
            d.rounded_rectangle((x + 11, y - 24, x + 23, y + 10), 5, fill=color)
            d.rounded_rectangle((x + 12, y - 2, x + 43, y + 26), 6, fill=color)
            d.rounded_rectangle((x - 2, y + 1, x + 9, y + 28), 3, fill=color)
            for n in range(3):
                d.line((x + 29, y + 6 + n * 7, x + 42, y + 6 + n * 7), fill=dark, width=2)
        else:
            raised = {"peace": (0, 1), "open": (0, 1, 2, 3), "fist": (),
                      "point": (0,)}.get(task, (0, 1, 2, 3))
            for n in range(4):
                top = y - (27 if n in (1, 2) else 21) if n in raised else y - 1
                bx = x + n * 11
                if task == "peace" and n == 0:
                    d.line((bx + 5, y + 8, bx - 2, top), fill=color, width=9)
                    d.ellipse((bx - 6, top - 4, bx + 2, top + 4), fill=color)
                else:
                    d.rounded_rectangle((bx, top, bx + 9, y + 15), 4, fill=color)
            d.rounded_rectangle((x - 1, y + 4, x + 43, y + 35), 9, fill=color)
            if task == "open":
                d.line((x + 4, y + 19, x - 12, y + 1), fill=color, width=10)
                d.ellipse((x - 16, y - 4, x - 6, y + 6), fill=color)
            else:
                d.line((x + 3, y + 18, x + 25, y + 12), fill=dark, width=3)
            d.line((x + 10, y + 38, x + 31, y + 38), fill=color, width=3)
        for n in range(3):
            a = t * 1.1 + n * 2.094
            sx, sy = cx + _nr_math.cos(a) * 43, cy + _nr_math.sin(a) * 36
            d.line((sx - 3, sy, sx + 3, sy), fill=color)
            d.line((sx, sy - 3, sx, sy + 3), fill=color)

    def _task_icon(self, d, task, color, t):
        if task in ("red", "blue", "green"):
            for radius in (36, 29):
                d.ellipse((184-radius, 69-radius, 184+radius, 69+radius),
                          outline=tuple(v // 3 for v in color), width=1)
            r = 24 + 2 * _nr_math.sin(t * 2)
            d.rounded_rectangle((184-r, 69-r, 184+r, 69+r), 9, fill=color)
            d.rounded_rectangle((167, 51, 179, 55), 2, fill=(255, 255, 255))
        elif task == "near":
            for n in range(3):
                r = 12 + ((t * 10 + n * 13) % 39)
                d.arc((184-r, 69-r, 184+r, 69+r), 210, 330, fill=color, width=2)
            d.rounded_rectangle((162, 65, 206, 90), 6, outline=color, width=3)
            d.ellipse((179, 73, 189, 83), fill=color)
        else:
            self._hand(d, 182, 66, task, color, t)

    def _scores(self, d, scores, t):
        items = sorted(scores.items(), key=lambda p: (-p[1], p[0]))
        if not items:
            return
        # Scroll sets of three for teams bigger than three instead of tiny type.
        if len(items) > 3:
            page = int(t / 3) % _nr_math.ceil(len(items) / 3)
            items = items[page * 3:page * 3 + 3]
        for i, (name, score) in enumerate(items):
            x = 10 + i * 75
            c = self.COLORS[i % 4]
            d.rounded_rectangle((x, 93, x+69, 127), 5, fill=(20, 22, 43), outline=c)
            self._text(d, (x+6, 96), name, 9, (197, 205, 222), width=56)
            self._text(d, (x+58, 107), score, 15, c, center=True)

    def render(self, view, now):
        image = self.base.copy()
        d = _NRDraw.Draw(image)
        t = float(now)
        phase = view.get("phase", "lobby")
        task = view.get("task", "peace")
        task = "open" if task == "palm" else task
        first, second, accent = self.TASKS.get(task, ("GET", "READY", self.COLORS[0]))
        if phase in ("result", "champion"):
            accent = self.COLORS[2]
        self._background(d, t, accent, phase in ("result", "champion"))
        self._header(d, view, accent)

        if phase == "lobby":
            title = str(view.get("title") or "NEON RACE")
            lines = title.split(" ", 1)
            self._text(d, (12, 30), lines[0], 31, self.COLORS[0], width=127)
            self._text(d, (12, 62), lines[1] if len(lines) > 1 else "", 31,
                       self.COLORS[1], width=127)
            for n in range(5):
                r = 14 + n * 6
                a = (t * (30 + 9*n) + n*58) % 360
                d.arc((183-r, 61-r, 183+r, 61+r), a, a+235, fill=self.COLORS[n % 4], width=2)
            self._text(d, (183, 48), str(view.get("players", 0)), 22, center=True)
            self._text(d, (183, 74), "PLAYERS", 8, center=True)
            d.rounded_rectangle((10, 103, 229, 127), 5, fill=(21, 28, 51))
            self._text(d, (120, 108), view.get("subtitle") or "TOP BUTTON / START", 11,
                       width=207, center=True)
        elif phase == "countdown":
            n = max(1, _nr_math.ceil(float(view.get("seconds", 3))))
            for i in range(4):
                r = 24 + i * 10 + _nr_math.sin(t * 2) * 2
                start = (t * 55 + i * 70) % 360
                d.arc((120-r, 75-r, 120+r, 75+r), start, start+190,
                      fill=self.COLORS[i], width=2)
            self._text(d, (120, 35), str(n), 63, center=True)
            self._text(d, (120, 113), "GET READY", 11, accent, center=True)
        elif phase == "playing":
            self._text(d, (12, 34), first, 24, width=132)
            self._text(d, (12, 60), second, 29, accent, width=134)
            self._task_icon(d, task, accent, t)
            d.rounded_rectangle((12, 103, 227, 110), 3, fill=(36, 40, 62))
            progress = max(0, min(1, float(view.get("progress", 0))))
            if progress:
                d.rounded_rectangle((12, 103, 12+max(3, int(215*progress)), 110), 3, fill=accent)
            subtitle = view.get("subtitle") or "HOLD IT STEADY"
            self._text(d, (12, 116), subtitle, 9, (181, 194, 219), width=161)
            self._text(d, (185, 114), "%.1fs" % max(0, view.get("seconds", 0)), 12, accent)
        elif phase == "locked":
            title = str(view.get("title") or "LOCKED IN!")
            success = title.upper().startswith("LOCKED")
            status_color = accent if success else (255, 179, 91)
            d.ellipse((96, 29, 144, 77), outline=status_color, width=2)
            if success:
                d.line((108, 53, 118, 63, 136, 41), fill=status_color, width=5)
            else:
                d.line((120, 37, 120, 53, 132, 59), fill=status_color, width=3)
                d.ellipse((118, 51, 122, 55), fill=status_color)
            self._text(d, (120, 81), title, 25, status_color, width=218, center=True)
            self._text(d, (120, 115), view.get("subtitle") or "WAITING FOR THE OTHERS", 10,
                       width=220, center=True)
        elif phase in ("result", "champion"):
            label = "MATCH CHAMPION" if phase == "champion" else "ROUND WINNER"
            winner = view.get("winner", "")
            if isinstance(winner, (tuple, list)):
                winner = " + ".join(str(x) for x in winner)
            title = view.get("title") or winner or "NO WINNER"
            self._text(d, (120, 29), label, 10, accent, center=True)
            self._text(d, (120, 43), title, 28, width=218, center=True)
            self._text(d, (120, 76), view.get("subtitle") or "FAST HANDS. BIG ENERGY.", 9,
                       width=220, center=True)
            self._scores(d, view.get("scores", {}), t)
        else:
            self._text(d, (120, 35), view.get("title") or "PAUSED", 25,
                       (255, 159, 112), width=220, center=True)
            self._text(d, (120, 76), view.get("subtitle") or "CHECK THE TERMINAL", 11,
                       width=218, center=True)
        return image


import argparse
import json
import os
import queue
import re
import socket
import sys
import threading
import time
import uuid
from pathlib import Path


class RaceParticipant:
    """Local monotonic timing. A held pose must be released before it can win."""

    def __init__(self, name, boot, send):
        self.name, self.boot, self.send = name, boot, send
        self.session, self.round = None, 0
        self.task, self.phase = "", "lobby"
        self.go_at, self.ends_at = 0.0, 0.0
        self.ready_sent, self.sent, self.armed = False, False, False
        self.hold_since = None
        self.progress = 0.0
        self.scores, self.roster, self.winners = {}, [], []
        self.players = []
        self.note = "Waiting for the host"
        self.last_host = 0.0
        self.completed = set()
        self.retired_sessions = set()
        self.master_boot, self.last_seq = None, -1
        self.retired_masters = set()

    def packet(self, **extra):
        return dict(player=self.name, boot=self.boot, session=self.session,
                    round=self.round, **extra)

    def receive(self, kind, data, now):
        session, rnd = data.get("session"), data.get("round")
        if (not isinstance(session, str) or not isinstance(rnd, int)
                or isinstance(rnd, bool) or not 0 <= rnd <= 5):
            return
        master_boot, seq = data.get("host_boot"), data.get("seq")
        if master_boot is not None:
            if not isinstance(master_boot, str) or not isinstance(seq, int):
                return
            if master_boot in self.retired_masters:
                return
            if master_boot != self.master_boot:
                if self.master_boot is not None:
                    self.retired_masters.add(self.master_boot)
                self.master_boot, self.last_seq = master_boot, -1
            if seq <= self.last_seq:
                return
            self.last_seq = seq
        if session in self.retired_sessions:
            return
        if session == self.session and rnd < self.round:
            return
        self.last_host = now
        if kind == "state":
            # State snapshots update the scoreboard, never restart a live round.
            if self.session is not None and session != self.session:
                if data.get("phase") != "lobby":
                    return
                self.retired_sessions.add(self.session)
                self.session, self.round = session, rnd
            self.scores = data.get("scores", self.scores)
            self.roster = data.get("roster", self.roster)
            self.players = data.get("players", self.players)
            if data.get("phase") in ("lobby", "error"):
                self.phase = "lobby"
                self.note = data.get("message") or data.get("error") or "Waiting for players"
            if data.get("phase") == "finished":
                self.phase = "champion"
                self.winners = data.get("champions", data.get("winners", []))
            return
        key = (session, rnd)
        if kind == "prepare":
            roster = data.get("roster", [])
            names = [p if isinstance(p, str) else p.get("player", "") for p in roster]
            if self.name not in names:
                self.note = "Join the next match"
                return
            if key in self.completed or (key[0] == self.session and key[1] < self.round):
                return
            if key != (self.session, self.round):
                if self.session is not None and self.session != session:
                    self.retired_sessions.add(self.session)
                self.session, self.round = key
                self.task = data["task"]
                self.phase = "arming"
                self.ready_sent = self.sent = self.armed = False
                self.hold_since, self.progress = None, 0.0
                self.roster = roster
                self.note = "Sensors getting ready"
            return
        if key != (self.session, self.round):
            return
        if kind == "go" and self.phase == "arming":
            self.go_at = now + float(data.get("delay", 3.0))
            self.ends_at = self.go_at + float(data.get("duration", 12.0))
            self.phase = "countdown"
        elif kind == "result" and key not in self.completed:
            self.completed.add(key)
            self.scores = data.get("scores", self.scores)
            self.winners = data.get("winners", [])
            self.phase = "result"
            self.note = data.get("message", "")

    def step(self, now, reading, caps):
        if self.phase == "arming" and self.task in caps:
            # Repeat ready until GO; QoS duplicates are harmless.
            if not self.ready_sent or now - self.ready_sent >= 1.0:
                if self.send("ready", self.packet()):
                    self.ready_sent = now
        if self.phase == "countdown" and now >= self.go_at:
            self.phase = "playing"
        if self.phase != "playing" or self.sent:
            return
        if now >= self.ends_at:
            self.phase, self.note = "locked", "Time is up"
            return
        camera_task = self.task in {"peace", "palm", "fist", "thumbs_up"}
        stamp = reading.get("gesture_updated" if camera_task else "color_updated", 0)
        if self.task == "near":
            stamp = reading.get("proximity_updated", stamp)
        fresh = self.task in caps and self.go_at <= stamp <= now and now - stamp < 0.8
        detected = reading.get("gesture") if camera_task else reading.get("color")
        matches = bool(reading.get("near")) if self.task == "near" else detected == self.task
        if not fresh:
            self.hold_since, self.progress = None, 0.0
            self.note = "Checking sensor..."
            return
        if not matches:
            self.armed = True
            self.hold_since, self.progress = None, 0.0
            self.note = "Make your move!"
            return
        if not self.armed:
            self.note = "Release first, then do it!"
            return
        if self.hold_since is None:
            self.hold_since = stamp
        # Several new readings must confirm the hold; one stalled frame cannot win.
        self.progress = min(1.0, max(0.0, (stamp - self.hold_since) / 0.35))
        self.note = "Hold it..."
        if self.progress >= 1.0:
            elapsed = now - self.go_at
            if self.send("done", self.packet(task=self.task, elapsed=round(elapsed, 4))):
                self.sent, self.phase = True, "locked"
                self.note = f"Locked in: {elapsed:.2f}s"


class NeonTransport:
    def __init__(self, args, boot):
        import paho.mqtt.client as mqtt
        self.args, self.boot = args, boot
        self.prefix = f"IDD/{args.team}/race"
        self.events = queue.Queue(maxsize=512)
        self.connected = False
        self.error = "Connecting to MQTT..."
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id=f"neon-{args.team}-{args.name}-{boot[:6]}",
                                  clean_session=True)
        self.client.username_pw_set(args.username, args.password)
        self.client.will_set(self.prefix + "/hello", json.dumps({
            "player": args.name, "boot": boot, "caps": [], "online": False}), qos=1)
        self.client.reconnect_delay_set(min_delay=1, max_delay=8)
        self.client.on_connect = self._connect
        self.client.on_disconnect = self._disconnect
        self.client.on_message = self._message
        self.client.connect_async(args.broker, args.port, keepalive=15)
        self.client.loop_start()

    def _connect(self, client, userdata, flags, reason, properties):
        self.connected = not reason.is_failure
        self.error = "" if self.connected else f"MQTT: {reason}"
        if self.connected:
            client.subscribe(self.prefix + "/#", qos=1)

    def _disconnect(self, client, userdata, flags, reason, properties):
        self.connected = False
        self.error = "MQTT disconnected - reconnecting"

    def _message(self, client, userdata, msg):
        if msg.retain or len(msg.payload) > 16384:
            return  # Game rounds are live events; never replay retained rounds.
        kind = msg.topic[len(self.prefix) + 1:]
        if kind not in {"hello", "ready", "done", "prepare", "go", "result", "state"}:
            return
        try:
            data = json.loads(msg.payload)
            if isinstance(data, dict):
                self.events.put_nowait((kind, data, time.monotonic()))
        except (ValueError, UnicodeError, queue.Full):
            pass

    def send(self, kind, data):
        if not self.connected:
            return False
        result = self.client.publish(self.prefix + "/" + kind,
                                     json.dumps(data, allow_nan=False),
                                     qos=0 if kind.startswith("sensor/") else 1,
                                     retain=False)
        return result.rc == 0

    def close(self):
        if self.connected:
            result = self.client.publish(self.prefix + "/hello", json.dumps({
                "player": self.args.name, "boot": self.boot, "caps": [], "online": False}), qos=1)
            try:
                result.wait_for_publish(timeout=1)
            except RuntimeError:
                pass
        self.client.disconnect()
        self.client.loop_stop()


class PracticeTransport:
    """Same game protocol, local queue. This mode does not meet the 3-Pi requirement."""
    def __init__(self):
        self.events, self.connected, self.error = queue.Queue(), True, ""

    def send(self, kind, data):
        if not kind.startswith("sensor/"):
            self.events.put((kind, data, time.monotonic()))
        return True

    def close(self):
        pass


def neon_args(argv=None):
    parser = argparse.ArgumentParser(description="NEON RACE: real sensors, big arcade energy. Lab 6.")
    parser.add_argument("--name", default="pi1", help="Unique name for this Pi: pi1, pi2, pi3")
    parser.add_argument("--team", default="stephen-neon", help="Same unique topic namespace on all Pis")
    parser.add_argument("--host", action="store_true", help="This Pi runs the game master AND plays")
    parser.add_argument("--master", default="pi1", help="Name of the one host Pi")
    parser.add_argument("--practice", action="store_true", help="One-Pi offline test with real sensors")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--no-camera", action="store_true")
    parser.add_argument("--no-sensor", action="store_true")
    parser.add_argument("--model", default=None, help="Optional local gesture_recognizer.task")
    parser.add_argument("--swap-buttons", action="store_true")
    parser.add_argument("--broker", default=os.getenv("MQTT_BROKER", "farlab.infosci.cornell.edu"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME", "idd"))
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD", "device@theFarm"))
    parser.add_argument("--preview", metavar="FILE", help="Render a PNG without Pi hardware")
    args = parser.parse_args(argv)
    for value in (args.name, args.team, args.master):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", value):
            parser.error("Names/team must be 1-32 letters, numbers, dashes or underscores")
    if len(args.name) > 24 or len(args.master) > 24:
        parser.error("Player names must be 24 characters or fewer")
    if len(args.name) > 24 or len(args.master) > 24:
        parser.error("Player names must be 24 characters or fewer")
    if args.practice:
        args.host, args.master = True, args.name
    if args.host and args.name != args.master:
        parser.error("The host's --name must match --master (normally pi1)")
    return args


def run_neon(argv=None):
    args = neon_args(argv)
    renderer = NeonRenderer()
    if args.preview:
        renderer.render(dict(phase="playing", title="PEACE SIGN", subtitle="Hold it...",
                             player="PI 1", round=2, total_rounds=5, progress=0.72,
                             seconds=8.2, scores={"pi1": 1, "pi2": 0, "pi3": 1},
                             task="peace", connected=True), 2.4).save(args.preview)
        print("Saved", args.preview)
        return
    screen = sensors = transport = journal = None
    try:
        screen = PiScreen()
        screen.draw(renderer.render(dict(phase="lobby", title="NEON RACE",
                    subtitle="Waking up camera + sensor", player=args.name), time.monotonic()))
        sensors = SensorInputs(camera=args.camera, no_camera=args.no_camera,
                               no_sensor=args.no_sensor, model_path=args.model)
        boot = uuid.uuid4().hex
        transport = PracticeTransport() if args.practice else NeonTransport(args, boot)
        player = RaceParticipant(args.name, boot, transport.send)
        host = RaceHost(min_players=1 if args.practice else 3, rounds=5) if args.host else None
        logdir = Path.home() / ".local" / "state" / "neon-race"
        logdir.mkdir(parents=True, exist_ok=True)
        journal = (logdir / f"{time.strftime('%Y%m%d-%H%M%S')}-{args.name}-{boot[:6]}.jsonl").open("a")
        print(f"NEON RACE | {args.name} | {'PRACTICE (offline)' if args.practice else 'IDD/' + args.team + '/race'}")
        print("Top: host starts match. Bottom: quit. Ctrl+C also exits.")
        print("Keep hands/colors neutral until GO, then perform and hold the task.")
        print("Camera frames stay on this Pi. Only gesture/color labels and timing go to MQTT.")
        last_hello = last_sensor = last_status = 0.0
        host_seq = 0
        button_quit_after = time.monotonic() + 1.0
        last_phase = ""
        while True:
            frame_start = now = time.monotonic()
            reading, caps = sensors.poll(), set(sensors.capabilities)
            initializing = any(reading.get(key) == "starting" for key in ("camera_status", "sensor_status"))
            if initializing:
                caps = set()  # Wait for both requested streams before negotiating challenges.
            if now - last_hello >= 2.0:
                transport.send("hello", dict(player=args.name, boot=boot, caps=sorted(caps), online=True))
                last_hello = now
            if now - last_sensor >= 0.5 and caps:
                transport.send("sensor/" + args.name, dict(player=args.name, boot=boot,
                    color=reading.get("color"), gesture=reading.get("gesture"),
                    near=reading.get("near", False), rgb=reading.get("rgb", (0, 0, 0))))
                last_sensor = now
            for _ in range(100):
                try:
                    kind, data, received = transport.events.get_nowait()
                except queue.Empty:
                    break
                if host and kind in {"hello", "ready", "done"}:
                    host.handle(kind, data, received)
                if kind in {"prepare", "go", "result", "state"} and data.get("host") == args.master:
                    player.receive(kind, data, received)
                if kind in {"prepare", "go", "done", "result"}:
                    journal.write(json.dumps(dict(at=time.time(), kind=kind, data=data)) + "\n")
                    journal.flush()
            top, bottom = screen.buttons()
            if args.swap_buttons:
                top, bottom = bottom, top
            if bottom and now >= button_quit_after:
                break
            if top and host:
                host.start(now)
            if host:
                host.tick(now)
                for kind, payload in host.drain():
                    host_seq += 1
                    transport.send(kind, dict(payload, host=args.name, host_boot=boot, seq=host_seq))
            # A disconnect cannot generate a winning event. The host times the round out.
            if transport.connected and now - player.last_host < 5.0:
                player.step(now, reading, caps)
            if not transport.connected:
                title, subtitle, phase = "RECONNECTING", transport.error, "error"
            elif initializing or not caps:
                title, subtitle, phase = "WARMING UP", reading.get("error") or "Camera / sensor starting...", "lobby"
            else:
                phase = player.phase
                title = {"peace": "PEACE SIGN", "palm": "OPEN PALM", "fist": "MAKE A FIST",
                         "thumbs_up": "THUMBS UP", "red": "SHOW RED", "green": "SHOW GREEN",
                         "blue": "SHOW BLUE", "near": "HAND CLOSE"}.get(player.task, "NEON RACE")
                subtitle = player.note
                if phase == "lobby":
                    title = "NEON RACE"
                    host_state = host.snapshot() if host else {}
                    count = len(host_state.get("players", [])) if host else len(player.players)
                    subtitle = ("SOLO PRACTICE / TOP: START" if args.practice else
                                f"{count} online / TOP: START" if args.host else "Waiting for host to start")
                    if args.host and host_state.get("message") not in {"Waiting for players", "Get ready"}:
                        subtitle = host_state.get("message", subtitle)
                elif phase == "arming":
                    phase, title, subtitle = "lobby", "GET READY", "Waiting for all sensors"
                elif phase == "countdown":
                    title, subtitle = str(max(1, int(player.go_at - now + 0.999))), "GET READY"
                elif phase == "result":
                    title = ("YOU WIN!" if args.name in player.winners else
                             "/".join(player.winners).upper() + " WINS" if player.winners else "TIME'S UP")
                    subtitle = "Round complete / next up..."
                elif phase == "champion":
                    winners = player.winners
                    title = "CHAMPION!" if args.name in winners else "MATCH OVER"
                    subtitle = (" + ".join(winners).upper() if winners else "NO WINNER") + " / TOP: REMATCH"
                elif phase == "locked":
                    title = "LOCKED IN!" if player.sent else "TIME'S UP"
                if now - player.last_host > 5.0:
                    phase, title, subtitle = "lobby", "FINDING HOST", f"Start {args.master} with --host"
            view = dict(phase=phase, title=title, subtitle=subtitle, task=player.task,
                        player=args.name + (" / SOLO" if args.practice else ""),
                        round=player.round, total_rounds=5, scores=player.scores,
                        winners=player.winners, progress=player.progress,
                        players=len(host.snapshot().get("players", [])) if host else len(player.players),
                        practice=args.practice,
                        seconds=max(0, player.go_at - now if phase == "countdown" else player.ends_at - now),
                        connected=transport.connected, rgb=reading.get("rgb", (0, 0, 0)))
            screen.draw(renderer.render(view, now))
            if phase != last_phase or now - last_status >= 10:
                print(f"{title} | {subtitle} | inputs: {','.join(sorted(caps)) or 'none'}", flush=True)
                if reading.get("error"):
                    print("Sensor status:", reading["error"], flush=True)
                last_status, last_phase = now, phase
            time.sleep(max(0, 1 / 20 - (time.monotonic() - frame_start)))
    except KeyboardInterrupt:
        print("\nGame stopped.")
    finally:
        if sensors:
            sensors.close()
        if transport:
            transport.close()
        if journal:
            journal.close()
        if screen:
            screen.close()


if __name__ == "__main__":
    try:
        run_neon()
    except Exception as exc:
        print(f"NEON RACE: {exc}", file=sys.stderr)
        sys.exit(1)
