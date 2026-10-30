import board, digitalio
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import st7789

cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
spi = board.SPI()
disp = st7789.ST7789(spi, cs=cs_pin, dc=dc_pin, rst=None, baudrate=64000000,
                     width=135, height=240, x_offset=53, y_offset=40)

backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output()
backlight.value = True

W, H = 240, 135  # landscape
ROT = 90

def _font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()

def show_text(lines, color="#FFFFFF", bg="#000000", size=18):
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    f = _font(size)
    y = 8
    for line in lines:
        d.text((8, y), line, font=f, fill=color)
        y += size + 6
    disp.image(img, ROT)

def show_image(path):
    img = Image.open(path).convert("RGB")
    img.thumbnail((W, H))
    canvas = Image.new("RGB", (W, H), "#FFFFFF")
    canvas.paste(img, ((W - img.width) // 2, (H - img.height) // 2))
    disp.image(canvas, ROT)

def light(on=True):
    backlight.value = on

if __name__ == "__main__":
    import time
    show_text(["PiTFT works!", "Night Noise", "Detector"], color="#7F77DD")
    time.sleep(3)
    show_image("noise_report.png")
    time.sleep(5)
    show_text(["Bye"])
