"""Screenshots for the site and App Store Connect from the Windows dev head.

  python tools/shots.py size              # only sizes the window to the iPhone client area
  python tools/shots.py capture uk song   # grabs the Strunika window into shots/raw/uk/song.png
  python tools/shots.py compose           # shots/raw/<lang>/*.png -> shots/appstore/<lang>/*.png (1290x2796)
                                          #                        -> assets/screens/<lang>/*.png  (640x1386)

capture: finds the window titled "Strunika", resizes it so the CLIENT area is
exactly 430x878 logical points (an iPhone 16 Pro Max minus the 54 pt status
bar; the home indicator is drawn over the bottom of the content, as on the phone), brings it to the front and saves the
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
NAMES = ["library", "song", "setlists", "live", "editor", "tuner", "dictionary"]

PT_W, PT_H = 430, 878          # client area in points: the phone's screen minus the status bar;
                               # the 34-pt home-indicator zone is part of it, the tab bar floats above it
STATUS_PT, HOME_PT = 54, 0     # the status bar is added above; the home indicator is drawn over the body
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
    if name is None:
        print(f"window set to {PT_W}x{PT_H} pt client (dpi {dpi})"); return

    client = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(client))
    pt = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    w, h = client.right, client.bottom
    # The MAUI window draws its content under the caption (the strip with the
    # window buttons), so the client area is taller than asked by exactly that
    # strip: it is cut off the top. Anything else is a real mismatch.
    caption = h - ch
    if w != cw or caption < 0 or caption > 60 * k:
        print(f"warning: client area is {w}x{h}, wanted {cw}x{ch}; the window may be clamped to the screen")
        caption = max(0, caption)
    img = ImageGrab.grab(bbox=(pt.x, pt.y + caption, pt.x + w, pt.y + h), all_screens=True).convert("RGB")
    (RAW / lang).mkdir(parents=True, exist_ok=True)
    out = RAW / lang / f"{name}.png"
    img.save(out)
    print(f"{out}  {img.width}x{img.height}  (dpi {dpi}, {k:.2f} px/pt)")


def _find_window(title: str):
    """The app's main window: titled like the app, or, since the MAUI window
    carries no title on Windows, the largest visible top-level window of the
    Strunika.Mobile process."""
    user32 = ctypes.windll.user32
    pids = set(_pids("Strunika.Mobile.exe"))
    found = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if buf.value == title or pid.value in pids:
            r = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            found.append(((r.right - r.left) * (r.bottom - r.top), hwnd))
        return True
    user32.EnumWindows(cb, 0)
    return max(found)[1] if found else None


def _pids(exe: str):
    import subprocess
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe}", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = line.strip().strip('"').split('","')
        if len(parts) > 1 and parts[0].lower() == exe.lower():
            try: yield int(parts[1])
            except ValueError: pass


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
        raw = _trim_window_edges(Image.open(f).convert("RGB"))
        body = raw.resize((OUT_W, PT_H * SCALE), Image.LANCZOS)
        top = _edge_colour(raw, "top")
        # The page background is one colour in Strunika and the status area at the
        # top is always bare background; the bottom row is not (a list can run to
        # the edge), so the home strip takes the top colour too.
        bottom = top
        canvas = Image.new("RGB", (OUT_W, OUT_H), top)
        canvas.paste(body, (0, STATUS_PT * SCALE))
        d = ImageDraw.Draw(canvas)
        ink = (255, 255, 255) if _lum(top) < 128 else (0, 0, 0)
        if not _status_bar_from_phone(canvas, ink):
            _status_bar(d, font, ink)
        # iOS tints the home indicator by what sits under it: white on the dark
        # pages, black when a light sheet (an exported PDF page) runs to the edge.
        home_ink = (255, 255, 255) if _lum(_edge_colour(raw, "bottom")) < 128 else (0, 0, 0)
        _home_indicator(d, home_ink)
        store = STORE / lang / f.name
        canvas.save(store, optimize=True)
        print(f"{lang}/{f.name}: {store} ({OUT_W}x{OUT_H})", end="")
        if f.stem in NAMES:
            site = SITE / lang / f.name
            canvas.resize((640, 1386), Image.LANCZOS).save(site, optimize=True)
            print(f", {site} (640x1386)", end="")
        print()


PHONE_BAR = ROOT / "shots" / "statusbar"       # time.png, signal.png, wifi.png, battery.png


def _status_bar_from_phone(canvas, ink):
    """The real thing: the time and the three icons cut from an iPhone screenshot
    at 3 px/pt (shots/statusbar/*.png, white on transparent, made from the
    user's IMG_3070/3071.PNG on 2026-10-20). Laid out the way a Pro Max lays
    them out, measured on Apple's own iPhone 16 Pro Max screenshot from the
    Apple Music App Store page (iOS 26): each cluster is centred in its "ear"
    beside the Dynamic Island — the time centred 78 pt from the left, the
    icons centred 348 pt from the left (signal, 8 pt, Wi-Fi, 11 pt, battery) —
    and everything is centred on the island's own middle, 29.5 pt down.
    Returns False when the files are missing."""
    from PIL import Image
    files = {n: PHONE_BAR / f"{n}.png" for n in ("time", "signal", "wifi", "battery")}
    if not all(p.exists() for p in files.values()):
        return False
    S = SCALE
    icons = {n: Image.open(p).convert("RGBA") for n, p in files.items()}
    def put(img, cx, cy):
        tint = Image.new("RGBA", img.size, ink + (0,))
        tint.putalpha(img.getchannel("A"))
        canvas.paste(tint, (round(cx - img.width / 2), round(cy - img.height / 2)), tint)
    cy = 29.5 * S
    put(icons["time"], 78 * S, cy)
    gaps = {"signal": 8 * S, "wifi": 11 * S, "battery": 0}
    total = sum(icons[n].width + gaps[n] for n in ("signal", "wifi", "battery"))
    x = 348 * S - total / 2
    for n in ("signal", "wifi", "battery"):
        img = icons[n]
        put(img, x + img.width / 2, cy)
        x += img.width + gaps[n]
    # Dynamic Island, as before
    from PIL import ImageDraw
    d = ImageDraw.Draw(canvas)
    cxi, w, h, top = PT_W * S / 2, 126 * S, 37 * S, 11 * S
    d.rounded_rectangle([cxi - w / 2, top, cxi + w / 2, top + h], radius=h / 2, fill=(0, 0, 0))
    return True


def _status_bar(d, font, ink):
    S = SCALE
    # time, centred in the left cluster like iOS
    # Measured on the user's iPhone 13 (2026-10-20): time centred ~66 pt from the left,
    # icons ending ~26 pt from the right, all centred ~27 pt down.
    d.text((68 * S, 27 * S), "9:41", fill=ink, font=font, anchor="mm")
    # Dynamic Island
    cx, w, h, top = PT_W * S / 2, 126 * S, 37 * S, 11 * S
    d.rounded_rectangle([cx - w / 2, top, cx + w / 2, top + h], radius=h / 2, fill=(0, 0, 0))
    # right cluster: signal, wi-fi, battery; sizes in points
    y = 27 * S
    x = (PT_W - 26) * S                     # right edge of the battery body
    # battery: 27x13 body, 2 pt radius, nub 2x5
    bw, bh = 27 * S, 13 * S
    d.rounded_rectangle([x - bw, y - bh / 2, x, y + bh / 2], radius=4 * S, outline=ink, width=max(1, int(1.2 * S)))
    d.rounded_rectangle([x - bw + 2 * S, y - bh / 2 + 2 * S, x - 2 * S, y + bh / 2 - 2 * S], radius=2.5 * S, fill=ink)
    d.rounded_rectangle([x + 1.5 * S, y - 2.5 * S, x + 3.5 * S, y + 2.5 * S], radius=1 * S, fill=ink)
    x -= bw + 8 * S
    # wi-fi: three arcs and a dot, drawn as thick arcs
    r = 8.5 * S
    cxw, cyw = x - r, y + 3 * S
    for rr, wdt in ((8.5, 2.2), (5.5, 2.2)):
        rr *= S
        d.arc([cxw - rr, cyw - rr, cxw + rr, cyw + rr], start=225, end=315, fill=ink, width=int(wdt * S))
    d.ellipse([cxw - 1.6 * S, cyw - 1.6 * S, cxw + 1.6 * S, cyw + 1.6 * S], fill=ink)
    x = cxw - r - 8 * S
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


def _trim_window_edges(img):
    """The Windows window leaves one or two black rows at the very top and bottom
    of the client capture (its frame). They would show as a dark seam under the
    status bar, so they are painted over with the colour of the row inside them."""
    from PIL import ImageDraw
    w, h = img.size
    d = ImageDraw.Draw(img)
    for rows in (range(0, 4), range(h - 1, h - 5, -1)):
        rows = list(rows)
        dark = [y for y in rows if _lum(_row_colour(img, y)) < 10]
        if dark and len(dark) < len(rows):
            inside = rows[len(dark)]
            d.rectangle([0, min(dark), w, max(dark)], fill=_row_colour(img, inside))
    # Windows 11 rounds the window's bottom corners (8 pt), and what shows through
    # the rounding is the desktop: the two corner squares are painted background.
    r = 12
    bgc = _row_colour(img, 4)
    d.rectangle([0, h - r, r, h], fill=bgc)
    d.rectangle([w - r, h - r, w, h], fill=bgc)
    return img


def _row_colour(img, y):
    w = img.size[0]
    px = [img.getpixel((x, y)) for x in range(0, w, max(1, w // 60))]
    return tuple(int(statistics.median(c[i] for c in px)) for i in range(3))


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
    if len(sys.argv) == 2 and sys.argv[1] == "size":
        capture(None, None)                      # resize and bring to front only
    elif len(sys.argv) == 4 and sys.argv[1] == "capture":
        lang, name = sys.argv[2], sys.argv[3]
        if name not in NAMES:
            print(f"note: '{name}' goes to the App Store set only; the site shows {NAMES}")
        capture(lang, name)
    elif len(sys.argv) == 2 and sys.argv[1] == "compose":
        compose()
    else:
        sys.exit(__doc__)
