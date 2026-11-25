"""App Store marketing frames: a caption and the whole phone on a warm ground
that runs from dark under the caption through copper to gold at the far end
(user, 2026-11-25: the old near-black ground hid the phone); the caption is
above the phone on odd frames and below it on even ones, and the ground is
turned over with it, so the light lettering always stands on the dark.

    python tools/montage.py [lang] [name]      (no args: every caption below)

Reads shots/appstore/<lang>/<name>.png (1290x2796, made by shots.py compose),
writes shots/store/<lang>/<nn>_<name>.png at the same size. Captions live in
CAPTIONS, in the order they go to App Store Connect; **word** is drawn in gold.
"""
import re, sys, random, pathlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "shots" / "appstore"
OUT = ROOT / "shots" / "store"
FONTS = pathlib.Path(r"D:\Projects\sideman\src\Strunika.Mobile\Resources\Fonts")
W, H = 1290, 2796

TEXT = (250, 234, 198)     # lettering on the dark band
TEXT2 = (224, 196, 150)
GOLD = (255, 204, 104)
BEZEL = (10, 8, 5)
RIM = (150, 116, 62)       # the phone's bronze rim
KEY_BODY, KEY_FACE, KEY_LIGHT = (96, 72, 38), (176, 138, 76), (226, 192, 124)   # side buttons
DIM = 0.84                 # the whole ground a step darker than first drawn


def ground(flip):
    """A mesh gradient: soft colour spots blurred into each other. Dark where the
    caption stands, copper ember and a dusty rose-brown through the middle, gold at
    the far end. flip: the caption is at the bottom and the ground is turned over.
    Built small and enlarged, then grained a little so the bands do not show."""
    def c(rgb): return tuple(int(v * DIM) for v in rgb)
    spots = [
        (0.50, 0.00, 0.95, 0.20, c((40, 24, 18))),
        (0.95, 0.42, 0.55, 0.26, c((150, 72, 38))),
        (0.00, 0.55, 0.50, 0.30, c((104, 50, 44))),
        (0.70, 1.00, 0.80, 0.30, c((188, 138, 52))),
        (0.05, 1.02, 0.45, 0.22, c((120, 62, 34))),
    ]
    if flip:
        spots = [(1 - x, 1 - y, rx, ry, col) for (x, y, rx, ry, col) in spots]
    sw, sh = 135, 240                                   # the trial's proportions (1080x1920 / 8)
    img = Image.new("RGB", (sw, sh), c((50, 30, 22)))
    gd = ImageDraw.Draw(img)
    for (cx, cy, rx, ry, colour) in spots:
        gd.ellipse([(cx - rx) * sw, (cy - ry) * sh, (cx + rx) * sw, (cy + ry) * sh], fill=colour)
    img = img.filter(ImageFilter.GaussianBlur(24)).resize((W, H), Image.BICUBIC)
    rnd = random.Random(7)
    noise = Image.frombytes("L", (W // 2, H // 2), bytes(118 + b % 20 for b in rnd.randbytes((W // 2) * (H // 2)))).resize((W, H))
    return Image.blend(img, Image.merge("RGB", (noise, noise, noise)), 0.035)

# (name, headline, subline) per frame, in store order
CAPTIONS = {
    "uk": [
        ("library",    "Обери пісню з **YouTube**,\nфайлу, медіатеки чи запису", "**ШІ** знайде акорди за кілька секунд"),
        ("song",       "Акорди пливуть\nпо звуковій доріжці", "Бери гітару, і грай"),
        ("live",       "Зіграй у мікрофон,\nі одразу побачиш акорд", "Режим Наживо"),
        ("sheet",      "Тональність,\nкапо, швидкість", "Міняй усе, не зупиняючи пісню"),
        ("editor",     "Поправ те,\nщо чуєш інакше", "Редактор акордів"),
        ("squares",    "Сітка тактів\nі бітів", "Бачиш структуру пісні цілком"),
        ("pdf_bars",   "Пісня на папері\nодним дотиком", "Експорт у PDF і не тільки"),
        ("setlists",   "Всі твої пісні\nв сетлістах", "У встановленому порядку"),
        ("tuner",      "Тюнер завжди\nпід рукою", "Точний і без зайвих кнопок"),
        ("dictionary", "168 акордів\nз діаграмами", "Словник акордів"),
    ],
    "en": [
        ("library",    "Pick a song from **YouTube**,\na file, your library or the mic", "**AI** finds its chords in seconds"),
        ("song",       "Chords flow\nalong the track", "Grab your guitar and play"),
        ("live",       "Play into the mic\nand see the chord at once", "Live mode"),
        ("sheet",      "Key, capo,\nspeed", "Change it all without stopping the song"),
        ("editor",     "Fix what you\nhear differently", "Chord editor"),
        ("squares",    "A grid of bars\nand beats", "See the whole shape of the song"),
        ("pdf_bars",   "The song on paper\nin one tap", "Export to PDF and more"),
        ("setlists",   "All your songs\nin setlists", "In the order you play them"),
        ("tuner",      "A tuner always\nat hand", "Precise, with no extra buttons"),
        ("dictionary", "168 chords\nwith diagrams", "Chord dictionary"),
    ],
}

HEAD_SIZE, HEAD_MIN, SIDE = 104, 80, 60     # headline px, smallest it may shrink to, side margin


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def _parts(line):
    """[(text, gold)] for a line with **gold** spans."""
    return [(t.strip("*"), t.startswith("**")) for t in re.split(r"(\*\*[^*]+\*\*)", line) if t]


def _width(d, line, f):
    return sum(d.textlength(t, font=f) for t, _ in _parts(line))


def _rich_line(d, cx, y, line, f):
    parts = _parts(line)
    widths = [d.textlength(t, font=f) for t, _ in parts]
    x = cx - sum(widths) / 2
    for (t, gold), w in zip(parts, widths):
        d.text((x, y), t, font=f, fill=GOLD if gold else TEXT, anchor="la")
        x += w


def montage(lang, name, head, sub, caption_top=True):
    shot = Image.open(SRC / lang / f"{name}.png").convert("RGB")
    canvas = ground(flip=not caption_top)
    d = ImageDraw.Draw(canvas)

    # the headline shrinks until its widest line fits between the side margins
    lines = head.split("\n")
    size = HEAD_SIZE
    f_head = font("Vollkorn-Bold.ttf", size)
    while size > HEAD_MIN and max(_width(d, l, f_head) for l in lines) > W - 2 * SIDE:
        size -= 2
        f_head = font("Vollkorn-Bold.ttf", size)
    leading = int(size * 1.19)
    f_sub = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 46)
    # the caption block is centred in the free zone between the frame's edge
    # and the phone's bezel, so the gaps above and below it are equal
    bezel, margin, top = 42, 66, 548                   # top: the screen's y when the caption is above
    zone = top - bezel                                 # free height either way
    text_h = leading * len(lines) + (26 + 56 if sub else 0)
    y = (zone - text_h) // 2 + (0 if caption_top else H - zone)
    for line in lines:
        _rich_line(d, W / 2, y, line, f_head)
        y += leading
    if sub:
        # the subline may have a **gold** word as well (AI, 2026-11-18)
        parts = _parts(sub)
        widths = [d.textlength(t, font=f_sub) for t, _ in parts]
        x = W / 2 - sum(widths) / 2
        for (t, gold), w in zip(parts, widths):
            d.text((x, y + 26), t, font=f_sub, fill=GOLD if gold else TEXT2, anchor="la")
            x += w

    # the phone: whole, the same size either way, in a bezel with side buttons
    sh = H - top - margin - bezel
    scale = sh / H
    sw = int(W * scale)
    py = top if caption_top else margin + bezel
    px = (W - sw) // 2
    screen = shot.resize((sw, sh), Image.LANCZOS)
    radius = int(165 * scale)
    body = [px - bezel, py - bezel, px + sw + bezel, py + sh + bezel]
    # action, volume up, volume down on the left, side button on the right;
    # offsets in screen points from the screen's top, as on a Pro Max
    # a shadow under the phone, so it stands off the lighter ground
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([body[0] + 8, body[1] + 36, body[2] - 8, body[3] + 48], radius + bezel, fill=(20, 10, 0, 150))
    canvas.paste(Image.alpha_composite(canvas.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(48))).convert("RGB"))
    d = ImageDraw.Draw(canvas)
    # bronze buttons with a lighter face and a line of light on the outer edge:
    # they read on the dark band and on the copper alike
    out, inn = 18, 11
    for side, y0, y1 in ((-1, 102, 132), (-1, 162, 228), (-1, 242, 308), (1, 182, 292)):
        ya, yb = py + int(y0 * 3 * scale), py + int(y1 * 3 * scale)
        box = [body[0] - out, ya, body[0] + inn, yb] if side < 0 else [body[2] - inn, ya, body[2] + out, yb]
        d.rounded_rectangle(box, 10, fill=KEY_BODY)
        face = [box[0] + 3, box[1] + 4, box[2] - 3, box[3] - 4]
        d.rounded_rectangle(face, 7, fill=KEY_FACE)
        light = [face[0] + 1, face[1] + 3, face[0] + 6, face[3] - 3] if side < 0 else [face[2] - 6, face[1] + 3, face[2] - 1, face[3] - 3]
        d.rounded_rectangle(light, 3, fill=KEY_LIGHT)
    # the body: a bronze rim, then the black bezel
    d.rounded_rectangle(body, radius + bezel, fill=RIM)
    inner = [body[0] + 6, body[1] + 6, body[2] - 6, body[3] - 6]
    d.rounded_rectangle(inner, radius + bezel - 6, fill=BEZEL, outline=(44, 34, 20), width=3)
    mask = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, sw - 1, sh - 1], radius, fill=255)
    canvas.paste(screen, (px, py), mask)
    return canvas


def main(argv):
    only = (argv[0], argv[1]) if len(argv) == 2 else None
    for lang, items in CAPTIONS.items():
        for i, (name, head, sub) in enumerate(items, 1):
            if only and (lang, name) != only: continue
            src = SRC / lang / f"{name}.png"
            if not src.exists():
                print(f"skip {lang}/{name}: no {src}"); continue
            out = OUT / lang / f"{i:02d}_{name}.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            tmp = out.with_suffix(".tmp.png")          # a viewer may hold the old file open
            montage(lang, name, head, sub, caption_top=(i % 2 == 1)).save(tmp, optimize=True)
            try: out.unlink()
            except FileNotFoundError: pass
            tmp.replace(out)
            print(out.relative_to(ROOT))


if __name__ == "__main__":
    main(sys.argv[1:])
