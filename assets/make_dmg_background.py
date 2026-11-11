"""Draws the DMG window background (1x and 2x PNGs).

usage: make_dmg_background.py OUT_DIR FONT_DIR
FONT_DIR holds Geist-SemiBold.ttf and Geist-Regular.ttf.
Layout must match dmg_settings.py: 660x420 window, icons centred at (180, 220) and (480, 220).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 660, 420
APP_X, APPS_X, ICON_Y = 180, 480, 220


BASE = (246, 246, 249)


def render(scale, fonts):
    s = lambda v: round(v * scale)  # noqa: E731
    # Light on purpose: Finder always draws the icon names in black on a custom background, even in dark mode.
    img = Image.new("RGB", (s(W), s(H)), BASE)

    # Ambient glows: rose top-left, indigo bottom-right.
    glow = Image.new("RGB", img.size, BASE)
    g = ImageDraw.Draw(glow)
    g.ellipse((s(-140), s(-180), s(320), s(220)), fill=(255, 196, 210))
    g.ellipse((s(380), s(200), s(840), s(580)), fill=(204, 206, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(s(100)))
    img = Image.blend(img, glow, 0.85)

    d = ImageDraw.Draw(img, "RGBA")

    # Frosted plate the two icons sit on.
    d.rounded_rectangle((s(70), s(128), s(W - 70), s(330)), radius=s(28),
                        fill=(255, 255, 255, 120), outline=(20, 20, 40, 18), width=max(1, s(1)))

    # Heading.
    title = ImageFont.truetype(str(fonts / "Geist-SemiBold.ttf"), s(22))
    sub = ImageFont.truetype(str(fonts / "Geist-Regular.ttf"), s(13))
    d.text((s(W / 2), s(52)), "YT Downloader", font=title, fill=(23, 23, 28), anchor="mm")
    d.text((s(W / 2), s(80)), "Drag the app into Applications to install", font=sub, fill=(105, 105, 118), anchor="mm")

    # Arrow between the icons: dotted track and a chevron in the accent colour.
    y = s(ICON_Y - 8)
    x0, x1 = s(APP_X + 78), s(APPS_X - 86)
    step = s(11)
    for i, x in enumerate(range(x0, x1 - s(10), step)):
        a = 70 + int(170 * i / max(1, (x1 - x0) // step))
        d.ellipse((x - s(2), y - s(2), x + s(2), y + s(2)), fill=(240, 69, 58, a))
    d.line([(x1 - s(12), y - s(10)), (x1, y), (x1 - s(12), y + s(10))],
           fill=(240, 69, 58, 245), width=s(3), joint="curve")

    # Footnote, kept clear of Finder's status bar when the user has it switched on.
    foot = ImageFont.truetype(str(fonts / "Geist-Regular.ttf"), s(11))
    d.text((s(W / 2), s(H - 54)),"First launch: right-click the app and choose Open",
           font=foot, fill=(130, 130, 142), anchor="mm")
    return img


if __name__ == "__main__":
    out, fonts = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    render(1, fonts).save(out / "dmg-bg.png")
    render(2, fonts).save(out / "dmg-bg@2x.png")
