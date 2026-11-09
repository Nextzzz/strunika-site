"""1024x1024 promotional image for the Strunika Pro subscriptions (App Store Connect).

Apple rejected the app icon as the subscription image (2.3.2), so this one shows
what Pro is: a chord card from the song screen plus the Pro features.
Usage: python tools/pro_promo.py  -> shots/store/subscription-pro-1024.png
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
FONTS = Path(r"D:\Projects\sideman\src\Strunika.Mobile\Resources\Fonts")
SRC = ROOT / "assets/screens/en/song.png"
OUT = ROOT / "shots/store/subscription-pro-1024.png"

S = 1024
BG_TOP, BG_BOT = (38, 30, 20), (20, 16, 11)
GOLD = (228, 184, 92)
CREAM = (240, 226, 196)

img = Image.new("RGB", (S, S))
d = ImageDraw.Draw(img)
for y in range(S):
    t = y / (S - 1)
    d.line([(0, y), (S, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOT)))

# soft gold glow behind the card
glow = Image.new("L", (S, S), 0)
ImageDraw.Draw(glow).ellipse((212, 260, 812, 860), fill=70)
glow = glow.filter(ImageFilter.GaussianBlur(120))
img = Image.composite(Image.new("RGB", (S, S), GOLD), img, glow)
d = ImageDraw.Draw(img)

# chord card cut from the song screen (chords + chip row, no album art)
shot = Image.open(SRC).convert("RGB")
card = shot.crop((20, 575, 620, 915))
scale = 1.25
card = card.resize((round(card.width * scale), round(card.height * scale)), Image.LANCZOS)
cw, ch = card.size
cx, cy = (S - cw) // 2, 310
mask = Image.new("L", card.size, 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, cw - 1, ch - 1), radius=48, fill=255)
shadow = Image.new("L", (S, S), 0)
ImageDraw.Draw(shadow).rounded_rectangle((cx, cy + 16, cx + cw, cy + ch + 16), radius=48, fill=150)
shadow = shadow.filter(ImageFilter.GaussianBlur(28))
img = Image.composite(Image.new("RGB", (S, S), (0, 0, 0)), img, shadow)
img.paste(card, (cx, cy), mask)
d = ImageDraw.Draw(img)
d.rounded_rectangle((cx, cy, cx + cw - 1, cy + ch - 1), radius=48, outline=(90, 72, 42), width=3)

bold = ImageFont.truetype(str(FONTS / "Vollkorn-Bold.ttf"), 112)
semi = ImageFont.truetype(str(FONTS / "Vollkorn-SemiBold.ttf"), 46)


def centered(text, font, y, fill):
    w = d.textlength(text, font=font)
    d.text(((S - w) / 2, y), text, font=font, fill=fill)


# title: "Strunika" + gold PRO pill
title = "Strunika"
pro = "PRO"
pro_font = ImageFont.truetype(str(FONTS / "Vollkorn-Bold.ttf"), 84)
tw = d.textlength(title, font=bold)
pw = d.textlength(pro, font=pro_font) + 56
gap = 28
x0 = (S - (tw + gap + pw)) / 2
d.text((x0, 92), title, font=bold, fill=CREAM)
px = x0 + tw + gap
d.rounded_rectangle((px, 112, px + pw, 222), radius=30, fill=GOLD)
d.text((px + 28, 108), pro, font=pro_font, fill=BG_BOT)

centered("Unlimited songs · Chord editor", semi, 810, CREAM)
centered("Export · Tunings · 168 chords", semi, 875, GOLD)

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT, "PNG")
print(OUT, img.size, img.mode)
