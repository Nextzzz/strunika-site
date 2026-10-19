"""Screenshots for the site and App Store Connect from the Windows dev head.

  python tools/shots.py capture uk song   # grabs the Strunika window into shots/raw/uk/song.png
  python tools/shots.py compose           # shots/raw/<lang>/*.png -> shots/appstore/<lang>/*.png (1290x2796)
                                          #                        -> assets/screens/<lang>/*.png  (640x1386)

capture: finds the window titled "Strunika", resizes it so the CLIENT area is
exactly 430x844 logical points (an iPhone 16 Pro Max minus the 54 pt status
bar and the 34 pt home-indicator strip), brings it to the front and saves the
client pixels. Run it from any terminal while the app is open on the screen
you want; it needs Pillow (pip install pillow).

compose: scales each raw capture to 1290 px wide, adds an iOS status bar
(9:41, Dynamic Island, signal, Wi-Fi, battery) above and the home indicator
below, both on the colour sampled from the capture's own edge, and writes
an opaque PNG. The 1290x2796 file is the 6.7"/6.9" App Store size; the site
copy is the same picture at 640x1386.
"""
import sys, time, pathlib, statistics, ctypes
from ctypes import wintypes

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "shots" / "raw"
STORE = ROOT / "shots" / "appstore"
SITE = ROOT / "assets" / "screens"
NAMES = ["song", "live", "editor", "tuner", "dictionary"]

PT_W, PT_H = 430, 844          # client area in points
STATUS_PT, HOME_PT = 54, 34    # strips added above and below
SCALE = 3                      # App Store pixels per point
OUT_W, OUT_H = PT_W * SCALE, (STATUS_PT + PT_H + HOME_PT) * SCALE   # 1290 x 2796


def capture(lang: str, name: str) -> None:
    from PIL import ImageGrab
    user32 = ctypes.windll.user32
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        user32.SetProcessDPIAware()

    hwnd = _find_window("Strunika")
    if not hwnd:
        sys.exit("No window titled 'Strunika' is open.")

    dpi = user32.GetDpiForWindow(hwnd) or 96
    k = dpi / 96
    cw, ch = round(PT_W * k), round(PT_H * k)

    style = user32.GetWindowLongW(hwnd, -16)
    exstyle = user32.GetWindowLongW(hwnd, -20)
    rect = wintypes.RECT(0, 0, cw, ch)
    user32.AdjustWindowRectExForDpi(ctypes.byref(rect), style, False, exstyle, dpi)
    ow, oh = rect.right - rect.left, rect.bottom - rect.top
    user32.ShowWindow(hwnd, 9)                      # SW_RESTORE
    user32.SetWindowPos(hwnd, 0, 40, 0, ow, oh, 0x0004 | 0x0040)   # SWP_NOZORDER | SWP_SHOWWINDOW
    user32.SetForegroundWindow(hwnd)
    time.sleep(1.2)                                 # let the layout settle and animations finish

    client = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(client))
    pt = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    w, h = client.right, client.bottom
    if (w, h) != (cw, ch):
        print(f"warning: client area is {w}x{h}, wanted {cw}x{ch}; the window may be clamped to the screen")
    img = ImageGrab.grab(bbox=(pt.x, pt.y, pt.x + w, pt.y + h), all_screens=True).convert("RGB")
    (RAW / lang).mkdir(parents=True, exist_ok=True)
    out = RAW / lang / f"{name}.png"
    img.save(out)
    print(f"{out}  {img.width}x{img.height}  (dpi {dpi}, {k:.2f} px/pt)")


def _find_window(title: str):
    user32 = ctypes.windll.user32
    found = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if buf.value == title:
                found.append(hwnd)
        return True
    user32.EnumWindows(cb, 0)
    return found[0] if found else None


# ---------------------------------------------------------------- compose

def compose() -> None:
    from PIL import Image, ImageDraw, ImageFont
    files = sorted(RAW.glob("*/*.png"))
    if not files:
        sys.exit(f"No captures in {RAW}/<lang>/")
    font = _font(17 * SCALE)
    for f in files:
        lang = f.parent.name
        (STORE / lang).mkdir(parents=True, exist_ok=True)
        (SITE / lang).mkdir(parents=True, exist_ok=True)
        raw = Image.open(f).convert("RGB")
        body = raw.resize((OUT_W, PT_H * SCALE), Image.LANCZOS)
        top = _edge_colour(raw, "top")
        bottom = _edge_colour(raw, "bottom")
        canvas = Image.new("RGB", (OUT_W, OUT_H), top)
        canvas.paste(body, (0, STATUS_PT * SCALE))
        d = ImageDraw.Draw(canvas)
        d.rectangle([0, (STATUS_PT + PT_H) * SCALE, OUT_W, OUT_H], fill=bottom)
        ink = (255, 255, 255) if _lum(top) < 128 else (0, 0, 0)
        _status_bar(d, font, ink)
        home_ink = (255, 255, 255) if _lum(bottom) < 128 else (0, 0, 0)
        _home_indicator(d, home_ink)
        store = STORE / lang / f.name
        canvas.save(store, optimize=True)
        print(f"{lang}/{f.name}: {store} ({OUT_W}x{OUT_H})", end="")
        if f.stem in NAMES:
            site = SITE / lang / f.name
            canvas.resize((640, 1386), Image.LANCZOS).save(site, optimize=True)
            print(f", {site} (640x1386)", end="")
        print()


def _status_bar(d, font, ink):
    S = SCALE
    # time, centred in the left cluster like iOS
    d.text((97 * S, 26 * S), "9:41", fill=ink, font=font, anchor="mm")
    # Dynamic Island
    cx, w, h, top = PT_W * S / 2, 126 * S, 37 * S, 11 * S
    d.rounded_rectangle([cx - w / 2, top, cx + w / 2, top + h], radius=h / 2, fill=(0, 0, 0))
    # right cluster: signal, wi-fi, battery; sizes in points
    y = 26 * S
    x = (PT_W - 14) * S                     # right edge of the battery body
    # battery: 27x13 body, 2 pt radius, nub 2x5
    bw, bh = 27 * S, 13 * S
    d.rounded_rectangle([x - bw, y - bh / 2, x, y + bh / 2], radius=4 * S, outline=ink, width=max(1, int(1.2 * S)))
    d.rounded_rectangle([x - bw + 2 * S, y - bh / 2 + 2 * S, x - 2 * S, y + bh / 2 - 2 * S], radius=2.5 * S, fill=ink)
    d.rounded_rectangle([x + 1.5 * S, y - 2.5 * S, x + 3.5 * S, y + 2.5 * S], radius=1 * S, fill=ink)
    x -= bw + 7 * S
    # wi-fi: three arcs and a dot, drawn as thick arcs
    r = 8.5 * S
    cxw, cyw = x - r, y + 3 * S
    for rr, wdt in ((8.5, 2.2), (5.5, 2.2)):
        rr *= S
        d.arc([cxw - rr, cyw - rr, cxw + rr, cyw + rr], start=225, end=315, fill=ink, width=int(wdt * S))
    d.ellipse([cxw - 1.6 * S, cyw - 1.6 * S, cxw + 1.6 * S, cyw + 1.6 * S], fill=ink)
    x = cxw - r - 7 * S
    # signal: four bars 3 pt wide, heights 4..12, gap 1.5
    bar_w, gap = 3 * S, 1.5 * S
    heights = (4, 6.5, 9, 12)
    total = 4 * bar_w + 3 * gap
    bx = x - total
    for i, hh in enumerate(heights):
        hh *= S
        d.rounded_rectangle([bx, y + 6 * S - hh, bx + bar_w, y + 6 * S], radius=1 * S, fill=ink)
        bx += bar_w + gap


def _home_indicator(d, ink):
    S = SCALE
    w, h = 139 * S, 5 * S
    cx = PT_W * S / 2
    y1 = OUT_H - 8 * S
    d.rounded_rectangle([cx - w / 2, y1 - h, cx + w / 2, y1], radius=h / 2, fill=ink)


def _edge_colour(img, edge):
    w, h = img.size
    y = 2 if edge == "top" else h - 3
    px = [img.getpixel((x, y)) for x in range(0, w, max(1, w // 60))]
    return tuple(int(statistics.median(c[i] for c in px)) for i in range(3))


def _lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _font(size):
    from PIL import ImageFont
    for name in ("segoeuisb.ttf", "seguisb.ttf", "segoeui.ttf", "arial.ttf"):
        p = pathlib.Path(r"C:\Windows\Fonts") / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "capture":
        lang, name = sys.argv[2], sys.argv[3]
        if name not in NAMES:
            print(f"note: '{name}' goes to the App Store set only; the site shows {NAMES}")
        capture(lang, name)
    elif len(sys.argv) == 2 and sys.argv[1] == "compose":
        compose()
    else:
        sys.exit(__doc__)
