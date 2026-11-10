"""One-off: turns a photo into data/portrait.txt (ASCII) for the hero card.

Run locally:  python3 scripts/make_portrait.py ~/Downloads/Ashmit_Passport.png   (needs Pillow)
Use a photo on a plain white background; white becomes blank space. The photo itself is never
committed, only the ASCII.
"""
import sys
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps

COLS = 150
CROP = (0.16, 0.10, 0.84, 0.84)  # fractions of the photo: head and shoulders of a passport-style shot
CELL = 1.82                      # mono cell height / width at the hero's font size and line height
RAMP = " .:-=+*#%@"
BLANK = 232                      # brighter than this is background
CURVE, GAIN = 2.0, 260          # tone curve (higher = lighter skin) and sharpening strength

im = Image.open(sys.argv[1]).convert("L")
w, h = im.size
im = im.crop((int(CROP[0] * w), int(CROP[1] * h), int(CROP[2] * w), int(CROP[3] * h)))
im = ImageOps.autocontrast(im, cutoff=1)
rows = round(COLS * im.height / im.width / CELL)
# Sharpen at the target size so eyes, brows and mouth keep their edges after downscaling.
sm = im.resize((COLS, rows), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.5, percent=GAIN, threshold=2))
# Plain brightness with a light-skewed curve: at ~3px type mid-tone skin must use sparse characters
# or the face turns into a grey block; hair, beard and features stay dense.
dark = lambda p: (BLANK - p) / BLANK
lines = ["".join(" " if p > BLANK else RAMP[1 + min(8, int(dark(p) ** CURVE * 9))] for p in (sm.getpixel((x, y)) for x in range(COLS))).rstrip()
         for y in range(rows)]
while lines and not lines[-1]:
    lines.pop()
out = Path(__file__).resolve().parent.parent / "data" / "portrait.txt"
out.write_text("\n".join(lines) + "\n")
print(f"wrote {len(lines)} rows x {COLS} cols to {out}")
