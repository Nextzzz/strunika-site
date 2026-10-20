"""Crop the Strunika window's client area out of a full screenshot:
   python tools/cropwin.py <screenshot.png> <lang> <name>
Finds the app background (#16110B) span near the bottom of the picture, takes
the last row where that colour still runs, and cuts a 538x1098-proportioned
client area above it (the caption strip with the window buttons stays out)."""
import sys, pathlib
from PIL import Image
src, lang, name = sys.argv[1:4]
im = Image.open(src).convert("RGB"); W, H = im.size; px = im.load()
isbg = lambda c: abs(c[0]-22) < 8 and abs(c[1]-17) < 8 and abs(c[2]-11) < 8
# the longest run of background pixels across several rows near the bottom: the window
best = (0, 0, 0)
for y in range(H - 60, H - 20, 5):
    run = 0
    for x in range(W + 1):
        if x < W and isbg(px[x, y]):
            run += 1
        else:
            if run > best[0]: best = (run, x - run, y)
            run = 0
_, left, y = best; right = left + best[0]
cx = (left + right) // 2
bottom = max(yy for yy in range(H) if isbg(px[cx, yy])) + 1
w = right - left; h = round(w * 1098 / 538)
out = pathlib.Path(__file__).resolve().parent.parent / "shots" / "raw" / lang / f"{name}.png"
out.parent.mkdir(parents=True, exist_ok=True)
im.crop((left, bottom - h, right, bottom)).save(out)
print(out, f"{w}x{h}")
