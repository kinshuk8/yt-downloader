"""Builds the README images in docs/: hero, icon, download button, and screenshots copied from screenshots.py.

usage: make_readme_art.py SHOTS_DIR FONT_DIR
SHOTS_DIR comes from screenshots.py (plus dmg.png, a capture of the installer window).
FONT_DIR holds Geist-SemiBold.ttf.
"""
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

shots, fonts = Path(sys.argv[1]), Path(sys.argv[2])
root = Path(__file__).resolve().parent.parent
docs = root / "docs"
docs.mkdir(exist_ok=True)
BASE = (246, 246, 249)


def hero():
    """Light and dark app windows overlapping on a soft gradient."""
    W, H = 2400, 1500
    img = Image.new("RGB", (W, H), BASE)
    glow = Image.new("RGB", (W, H), BASE)
    g = ImageDraw.Draw(glow)
    g.ellipse((-400, -500, 1300, 900), fill=(255, 190, 206))
    g.ellipse((1100, 500, 2900, 2000), fill=(200, 202, 255))
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(260)), 0.9).convert("RGBA")

    def place(shot, x, y, scale):
        win = Image.open(shot).convert("RGBA")
        win = win.resize((round(win.width * scale), round(win.height * scale)), Image.LANCZOS)
        # Soft macOS-style shadow from the window's own shape.
        shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        mask = win.split()[3].point(lambda a: 90 if a else 0)
        shadow.paste((20, 20, 40, 255), (x, y + 40), mask)
        img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(50)))
        img.alpha_composite(win, (x, y))

    place(shots / "app-light.png", 400, 130, 0.84)
    place(shots / "done-dark.png", 1040, 230, 0.84)
    img.convert("RGB").resize((W // 2, H // 2), Image.LANCZOS).save(docs / "hero.png", optimize=True)


def download_button(label, filename):
    """Coral download pill matching the app's primary button, drawn at 2x."""
    W, H, pad = 640, 128, 16
    img = Image.new("RGBA", (W + pad * 2, H + pad * 3), (0, 0, 0, 0))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((pad + 20, pad + 24, pad + W - 20, pad + H + 8), radius=40, fill=(240, 69, 58, 110))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14)))

    grad = Image.new("RGBA", (W, H))
    top, bottom = (255, 106, 77), (232, 58, 48)
    for y in range(H):
        t = y / H
        grad.paste(tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)) + (255,), (0, y, W, y + 1))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, W - 1, H - 1), radius=32, fill=255)
    img.paste(grad, (pad, pad), mask)

    d = ImageDraw.Draw(img)
    d.rounded_rectangle((pad, pad, pad + W - 1, pad + H - 1), radius=32, outline=(255, 255, 255, 50), width=2)
    # Download glyph (arrow over a tray) + label, centred together.
    font = ImageFont.truetype(str(fonts / "Geist-SemiBold.ttf"), 40)
    glyph_w, gap = 40, 24
    text_w = d.textlength(label, font=font)
    x0 = pad + (W - (glyph_w + gap + text_w)) / 2
    cx, cy = x0 + glyph_w / 2, pad + H // 2
    white = (255, 255, 255, 255)
    d.line([(cx, cy - 24), (cx, cy + 8)], fill=white, width=7)
    d.line([(cx - 14, cy - 5), (cx, cy + 9), (cx + 14, cy - 5)], fill=white, width=7, joint="curve")
    d.line([(cx - 20, cy + 24), (cx + 20, cy + 24)], fill=white, width=7)
    d.text((x0 + glyph_w + gap, cy), label, font=font, fill=white, anchor="lm")
    img.save(docs / filename, optimize=True)


def icon():
    subprocess.run([sys.executable, str(root / "assets" / "make_icon.py"), str(docs / "icon-1024.png")], check=True, capture_output=True)
    Image.open(docs / "icon-1024.png").resize((256, 256), Image.LANCZOS).save(docs / "icon.png", optimize=True)
    (docs / "icon-1024.png").unlink()


def screenshots():
    for name in ("app-light", "app-dark", "done-light", "done-dark"):
        Image.open(shots / f"{name}.png").save(docs / f"{name}.png", optimize=True)
    if (shots / "dmg.png").exists():
        shutil.copy(shots / "dmg.png", docs / "installer.png")


hero()
download_button("Download for Mac", "download-mac.png")
download_button("Download for Windows", "download-windows.png")
icon()
screenshots()
print(f"Wrote images to {docs}")
