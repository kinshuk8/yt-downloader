"""Draws the app icon (red rounded square, white download arrow over a tray) to icon.png."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

S = 1024
out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name("icon.png"))

# macOS icons sit on an 824px rounded square centred in the 1024 canvas, with a soft shadow.
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
box = (100, 100, 924, 924)

shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ImageDraw.Draw(shadow).rounded_rectangle((100, 112, 924, 936), radius=185, fill=(0, 0, 0, 90))
img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14)))

# Vertical gradient, bright coral to deep red.
grad = Image.new("RGBA", (S, S))
top, bottom = (255, 92, 77), (196, 22, 28)
for y in range(S):
    t = y / S
    grad.paste(tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)) + (255,), (0, y, S, y + 1))
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle(box, radius=185, fill=255)
img.paste(grad, (0, 0), mask)

d = ImageDraw.Draw(img)
white = (255, 255, 255, 255)
# Download arrow: rounded shaft + head.
d.rounded_rectangle((466, 250, 558, 520), radius=46, fill=white)
d.polygon([(332, 470), (692, 470), (512, 650)], fill=white)
# Tray under it.
d.rounded_rectangle((300, 712, 724, 772), radius=30, fill=white)

img.save(out)
print(f"Wrote {out}")
