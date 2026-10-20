"""App Store marketing frames: a caption and the whole phone on the brand's
dark background, the caption above the phone on odd frames and below it on
even ones.

    python tools/montage.py [lang] [name]      (no args: every caption below)

Reads shots/appstore/<lang>/<name>.png (1290x2796, made by shots.py compose),
writes shots/store/<lang>/<nn>_<name>.png at the same size. Captions live in
CAPTIONS, in the order they go to App Store Connect; **word** is drawn in gold.
"""
import re, sys, pathlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "shots" / "appstore"
OUT = ROOT / "shots" / "store"
FONTS = pathlib.Path(r"D:\Projects\sideman\src\Strunika.Mobile\Resources\Fonts")
W, H = 1290, 2796

BG = (22, 17, 11)          # --bg
TEXT = (233, 211, 162)     # --text
TEXT2 = (164, 143, 102)    # --text2
GOLD = (217, 172, 76)      # --accent
BEZEL = (10, 8, 5)
BEZEL_EDGE = (58, 46, 28)  # --sep
KEY = (26, 21, 13)         # side-button face

# (name, headline, subline) per frame, in store order
CAPTIONS = {
    "uk": [
        ("library",    "Обери пісню з **YouTube**,\nфайлу, медіатеки чи запису", "І за кілька секунд отримай акорди"),
        ("song",       "Акорди пливуть\nпо звуковій доріжці", "Бери гітару, і грай"),
        ("live",       "Зіграй у мікрофон,\nі одразу побачиш акорд", "Режим Live"),
        ("sheet",      "Тональність,\nкапо, швидкість", "Міняй усе, не зупиняючи пісню"),
        ("editor",     "Поправ те,\nщо чуєш інакше", "Редактор акордів і долей"),
        ("squares",    "Сітка тактів\nі бітів", "Бачиш структуру пісні цілком"),
        ("pdf_bars",   "Пісня на папері\nодним кліком", "Експорт у PDF і не тільки"),
        ("setlists",   "Всі твої пісні\nв сетлістах", "У встановленому порядку"),
        ("tuner",      "Тюнер завжди\nпід рукою", "Точний і без зайвих кнопок"),
        ("dictionary", "168 акордів\nз діаграмами", "Словник акордів"),
    ],
    "en": [
        ("library",    "Pick a song from **YouTube**,\na file, your library or the mic", "And get its chords in seconds"),
        ("song",       "Chords flow\nalong the track", "Grab your guitar and play"),
        ("live",       "Play into the mic\nand see the chord at once", "Live mode"),
        ("sheet",      "Key, capo,\nspeed", "Change it all without stopping the song"),
        ("editor",     "Fix what you\nhear differently", "Chord and beat editor"),
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
    canvas = Image.new("RGB", (W, H), BG)

    # a soft gold glow behind the phone
    glow = Image.new("RGB", (W, H), BG)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-200, 1500, W + 200, 3400], fill=(52, 38, 16))
    glow = glow.filter(ImageFilter.GaussianBlur(220))
    canvas.paste(glow)
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
    bezel, margin = 34, 90
    zone = H - (H - 600 - margin - bezel) - 2 * bezel - margin      # free height either way
    text_h = leading * len(lines) + (26 + 56 if sub else 0)
    y = (zone - text_h) // 2 + (0 if caption_top else H - zone)
    for line in lines:
        _rich_line(d, W / 2, y, line, f_head)
        y += leading
    if sub:
        d.text((W / 2, y + 26), sub, font=f_sub, fill=TEXT2, anchor="ma")

    # the phone: whole, the same size either way, in a bezel with side buttons
    sh = H - 600 - margin - bezel
    scale = sh / H
    sw = int(W * scale)
    py = 600 if caption_top else margin + bezel
    px = (W - sw) // 2
    screen = shot.resize((sw, sh), Image.LANCZOS)
    radius = int(165 * scale)
    body = [px - bezel, py - bezel, px + sw + bezel, py + sh + bezel]
    # action, volume up, volume down on the left, side button on the right;
    # offsets in screen points from the screen's top, as on a Pro Max
    out, thick = int(9 * scale * 3), int(3 * scale * 3)
    for side, y0, y1 in ((-1, 102, 132), (-1, 162, 228), (-1, 242, 308), (1, 182, 292)):
        ya, yb = py + int(y0 * 3 * scale), py + int(y1 * 3 * scale)
        box = [body[0] - out, ya, body[0] + thick, yb] if side < 0 else [body[2] - thick, ya, body[2] + out, yb]
        d.rounded_rectangle(box, thick, fill=BEZEL_EDGE)
        d.rounded_rectangle([box[0] + 2, box[1] + 2, box[2] - 2, box[3] - 2], thick, fill=KEY)
    d.rounded_rectangle(body, radius + bezel, fill=BEZEL, outline=BEZEL_EDGE, width=3)
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
