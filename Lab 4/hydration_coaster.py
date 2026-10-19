import time
import subprocess
from collections import deque

import board
import busio
import adafruit_ssd1306
import qwiic_proximity
import pi_servo_hat
from PIL import Image, ImageDraw, ImageFont

# Hydration Nudge Coaster
# 1. OLED says "Place your glass".
# 2. Put the glass on the coaster and a 20 second countdown starts.
# 3. At 0, the servo taps the glass and the speaker says "Drink water!"
# 4. Lift the glass and it goes back to "Place your glass".

COUNTDOWN_SECONDS = 10

# Measured: empty ~1-3, glass 1cm above ~5100, glass touching ~21600
CUP_THRESHOLD = 1000          # above this = glass is on the coaster
CUP_RELEASE = 500             # below this = glass is lifted

# Servo (channel 0 on the Servo pHAT). Tune these on your build.
SERVO_CH = 0
SERVO_REST = 20               # arm pulled back, away from the glass
SERVO_TAP = 75                # arm touching the glass

# ---------------- Setup ----------------

prox = qwiic_proximity.QwiicProximity()
if not prox.connected:
    raise RuntimeError("Proximity sensor not found. Check the Qwiic cable.")
prox.begin()

servo = pi_servo_hat.PiServoHat()
servo.restart()
servo.move_servo_position(SERVO_CH, SERVO_REST)

i2c = busio.I2C(board.SCL, board.SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)
image = Image.new("1", (oled.width, oled.height))
draw = ImageDraw.Draw(image)
font = ImageFont.load_default()


def show(line1, line2=""):
    draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)
    draw.text((0, 2), line1, font=font, fill=255)
    draw.text((0, 18), line2, font=font, fill=255)
    oled.image(image)
    oled.show()


def say(text):
    subprocess.Popen(["espeak", "-a", "200", text],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


TAP_TIMES = 4                 # how many times the arm taps
TAP_DELAY = 0.2               # seconds per swing (smaller = faster)


def tap():
    for _ in range(TAP_TIMES):
        servo.move_servo_position(SERVO_CH, SERVO_TAP)
        time.sleep(TAP_DELAY)
        servo.move_servo_position(SERVO_CH, SERVO_REST)
        time.sleep(TAP_DELAY)


readings = deque(maxlen=5)


def glass_on(currently_on):
    readings.append(prox.get_proximity())
    avg = sum(readings) / len(readings)
    if currently_on:
        return avg > CUP_RELEASE
    return avg > CUP_THRESHOLD


# ---------------- Main loop ----------------

glass = False
start = None
done = False

show("Hydration Coaster", "Place your glass")
print("Ready. Place a glass on the coaster.")

try:
    while True:
        was_on = glass
        glass = glass_on(glass)

        if glass and not was_on:
            start = time.time()
            done = False
            print("Glass placed. Countdown started.")

        if not glass:
            if was_on:
                print("Glass lifted.")
            show("Hydration Coaster", "Place your glass")
        elif not done:
            remaining = COUNTDOWN_SECONDS - (time.time() - start)
            if remaining > 0:
                show("Countdown", f"{int(remaining) + 1} seconds")
            else:
                show("Drink water!")
                say("Drink water!")
                tap()
                done = True
                print("Tap! Drink water!")

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nStopping.")
    servo.move_servo_position(SERVO_CH, SERVO_REST)
    show("Goodbye!")
