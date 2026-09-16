import time
import math
import digitalio
import board
from PIL import Image, ImageDraw, ImageFont
import adafruit_rgb_display.st7789 as st7789

# ---- Display setup ----
cs_pin = digitalio.DigitalInOut(board.D5)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = None
BAUDRATE = 64000000
spi = board.SPI()

disp = st7789.ST7789(
    spi,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
    width=135,
    height=240,
    x_offset=53,
    y_offset=40,
)

height = disp.width
width = disp.height
image = Image.new("RGB", (width, height))
rotation = 90
draw = ImageDraw.Draw(image)

draw.rectangle((0, 0, width, height), outline=0, fill=(0, 0, 0))
disp.image(image, rotation)

small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
time_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)

backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output()
backlight.value = True

# ---- Settings ----
BACKGROUND_COLOR = (10, 10, 20)
WATER_COLOR = (30, 90, 200)
DROPLET_COLOR = (120, 180, 250)
RIPPLE_COLOR = (150, 200, 255)
CLOUD_COLOR = (200, 200, 210)
TICK_COLOR = "#AAAAAA"
TEXT_COLOR = "#FFFFFF"
SHARK_COLOR = (60, 60, 70)

DROP_INTERVAL = 5
WATER_RISE_PER_DROP = height // 10
DROP_FALL_DURATION = 0.8
FRAME_DELAY = 0.05

WAVE_AMPLITUDE = 4
WAVE_LENGTH = 40
WAVE_SPEED = 2

SHARK_INTERVAL = 15
SHARK_SWIM_DURATION = 4

RIPPLE_TRAVEL_TIME = 2.5
NUM_RIPPLE_RINGS = 5
RIPPLE_STAGGER = 0.3
RIPPLE_MAX_RADIUS = width * 1.1

HOUR_MARKS = [(0, "12AM"), (4, "4AM"), (8, "8AM"), (12, "12PM"), (16, "4PM"), (20, "8PM"), (24, "12AM")]

drop_x = width // 2
cloud_bottom_y = 26

last_drop_time = time.time()
drop_active = False
drop_start_time = 0
ripple_active = False
ripple_start_time = 0
RIPPLE_TOTAL_DURATION = RIPPLE_TRAVEL_TIME + (NUM_RIPPLE_RINGS - 1) * RIPPLE_STAGGER

last_shark_time = time.time()
shark_active = False
shark_start_time = 0

current_water_height = 0
start_time = time.time()

def draw_cloud(cx, bottom_y):
    draw.ellipse((cx - 22, bottom_y - 16, cx + 2, bottom_y + 2), fill=CLOUD_COLOR)
    draw.ellipse((cx - 6, bottom_y - 22, cx + 18, bottom_y + 2), fill=CLOUD_COLOR)
    draw.ellipse((cx + 4, bottom_y - 14, cx + 26, bottom_y + 2), fill=CLOUD_COLOR)
    draw.ellipse((cx - 16, bottom_y - 10, cx + 16, bottom_y + 4), fill=CLOUD_COLOR)

def draw_water(water_top, t):
    points = []
    for px in range(0, width + 1, 4):
        wy = water_top + WAVE_AMPLITUDE * math.sin((px / WAVE_LENGTH) + t * WAVE_SPEED)
        points.append((px, wy))
    points.append((width, height))
    points.append((0, height))
    draw.polygon(points, fill=WATER_COLOR)

def draw_shark(cx, cy):
    draw.ellipse((cx - 18, cy - 7, cx + 14, cy + 7), fill=SHARK_COLOR)
    draw.polygon([(cx - 18, cy), (cx - 28, cy - 8), (cx - 28, cy + 8)], fill=SHARK_COLOR)
    draw.polygon([(cx, cy - 6), (cx + 6, cy - 18), (cx + 10, cy - 6)], fill=SHARK_COLOR)

def lerp_color(c1, c2, f):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * f) for i in range(3))

while True:
    now_ts = time.time()
    t = now_ts - start_time

    water_top = height - current_water_height

    draw.rectangle((0, 0, width, height), outline=0, fill=BACKGROUND_COLOR)
    draw_water(water_top, t)

    for hour, label in HOUR_MARKS:
        y = height - (hour / 24) * height
        y = max(1, min(height - 1, y))
        draw.line((width - 34, y, width - 26, y), fill=TICK_COLOR)
        draw.text((width - 4, y), label, font=small_font, fill=TICK_COLOR, anchor="rm")

    draw_cloud(drop_x, cloud_bottom_y)

    if not drop_active and not ripple_active and (now_ts - last_drop_time) >= DROP_INTERVAL:
        drop_active = True
        drop_start_time = now_ts
        last_drop_time = now_ts

    if drop_active:
        elapsed = now_ts - drop_start_time
        progress = min(elapsed / DROP_FALL_DURATION, 1.0)
        drop_y = int(cloud_bottom_y + progress * (water_top - cloud_bottom_y))
        draw.ellipse((drop_x - 4, drop_y - 6, drop_x + 4, drop_y + 6), fill=DROPLET_COLOR)
        if progress >= 1.0:
            drop_active = False
            ripple_active = True
            ripple_start_time = now_ts
            current_water_height = min(current_water_height + WATER_RISE_PER_DROP, height)

    if ripple_active:
        r_elapsed = now_ts - ripple_start_time

        for i in range(NUM_RIPPLE_RINGS):
            ring_elapsed = r_elapsed - i * RIPPLE_STAGGER
            if ring_elapsed < 0 or ring_elapsed > RIPPLE_TRAVEL_TIME:
                continue

            ring_progress = ring_elapsed / RIPPLE_TRAVEL_TIME
            radius = int(ring_progress * RIPPLE_MAX_RADIUS)
            ring_color = lerp_color(RIPPLE_COLOR, WATER_COLOR, ring_progress)

            if radius > 0:
                # Only draw the bottom half of the ellipse (0 to 180 degrees),
                # so the ripple stays within/below the water line instead of
                # poking up into the black background above it.
                draw.arc(
                    (drop_x - radius, water_top - radius // 4,
                     drop_x + radius, water_top + radius // 4),
                    start=0,
                    end=180,
                    fill=ring_color,
                )

        if r_elapsed >= RIPPLE_TOTAL_DURATION:
            ripple_active = False

    # --- Shark logic ---
    if not shark_active and (now_ts - last_shark_time) >= SHARK_INTERVAL:
        shark_active = True
        shark_start_time = now_ts
        last_shark_time = now_ts

    if shark_active:
        s_elapsed = now_ts - shark_start_time
        s_progress = min(s_elapsed / SHARK_SWIM_DURATION, 1.0)
        shark_x = int(-30 + s_progress * (width + 60))
        shark_y = min(water_top + 20, height - 15)

        draw_shark(shark_x, shark_y)

        current_time_str = time.strftime("%H:%M:%S")
        draw.text((shark_x - 20, shark_y - 30), current_time_str, font=time_font, fill=TEXT_COLOR)

        if s_progress >= 1.0:
            shark_active = False

    disp.image(image, rotation)
    time.sleep(FRAME_DELAY)
