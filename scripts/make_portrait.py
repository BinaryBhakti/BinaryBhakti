"""One-off: turns the GitHub avatar into data/portrait.txt (ASCII) for the hero card.
Run locally when the avatar changes: python3 scripts/make_portrait.py  (needs Pillow)."""
import io, json, subprocess, urllib.request
from pathlib import Path
from PIL import Image

COLS, CROP = 112, (100, 138, 300, 345)  # crop box tuned to the current avatar: head and shoulders
RAMP = " .:-=+*#%@"
url = json.loads(subprocess.run(["gh", "api", "users/BinaryBhakti"], capture_output=True, text=True, check=True).stdout)["avatar_url"]
im = Image.open(io.BytesIO(urllib.request.urlopen(url + "&s=400").read())).convert("RGB").crop(CROP)
rows = int(COLS * im.height / im.width * 0.5)  # mono cells are about twice as tall as wide
sm = im.resize((COLS, rows), Image.LANCZOS)

# The wall is one flat colour, so anything far from it in RGB is the figure. Skin is as bright
# as the wall, which is why a plain brightness cut-off loses the face.
edge = [sm.getpixel((x, y)) for y in range(rows) for x in (0, 1, COLS - 2, COLS - 1)]
wall = [sorted(c[i] for c in edge)[len(edge) // 2] for i in range(3)]


px = [[sm.getpixel((x, y)) for x in range(COLS)] for y in range(rows)]
figure = lambda p: sum((a - b) ** 2 for a, b in zip(p, wall)) ** .5 >= 38
lum = lambda p: (p[0] * 299 + p[1] * 587 + p[2] * 114) // 1000
# Stretch contrast over the figure only, so the dark suit and the face both get texture.
ls = sorted(lum(p) for row in px for p in row if figure(p))
lo, hi = ls[len(ls) // 50], ls[-len(ls) // 50]
grid = [[RAMP[1 + min(8, max(0, (hi - lum(p)) * 9 // max(1, hi - lo)))] if figure(p) else " " for p in row] for row in px]
# Keep only the person. Wall seams and the sign's edge are thin lines that touch the figure, so:
# erode (thin lines vanish), take the largest connected shape, then grow it back by one cell.
N8 = [(i, j) for i in (-1, 0, 1) for j in (-1, 0, 1) if i or j]
marked = {(x, y) for y in range(rows) for x in range(COLS) if grid[y][x] != " "}
core = {(x, y) for x, y in marked if sum((x + i, y + j) in marked for i, j in N8) >= 7}
seen, best = set(), set()
for start in core:
    if start in seen:
        continue
    comp, stack = set(), [start]
    while stack:
        p = stack.pop()
        if p in seen or p not in core:
            continue
        seen.add(p); comp.add(p)
        stack += [(p[0] + i, p[1] + j) for i, j in N8]
    best = max(best, comp, key=len)
keep = best | {(x + i, y + j) for x, y in best for i, j in N8}
lines = ["".join(c if (x, y) in keep else " " for x, c in enumerate(row)).rstrip() for y, row in enumerate(grid)]
while lines and not lines[0]:
    lines.pop(0)
out = Path(__file__).resolve().parent.parent / "data" / "portrait.txt"
out.write_text("\n".join(lines) + "\n")
print(f"wrote {len(lines)} rows to {out}")
