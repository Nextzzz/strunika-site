"""An exported PDF as a phone frame for the App Store set.

    python tools/pdfshot.py <lang> <name> [file.pdf]

Takes the newest PDF from the app's export cache (or the given file), keeps a
copy in shots/pdf/<lang>/<name>.pdf and renders shots/raw/<lang>/<name>.png the
way iOS shows a document: the song title on top, page 1 full width on the
app's dark background, page 2 starting below it and running off the frame.
The frame is drawn at 3 px/pt so compose does not have to upscale the type.
Then run `python tools/shots.py compose` as usual.
"""
import os, sys, pathlib, shutil
from PIL import Image, ImageDraw
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from shots import RAW, ROOT, PT_W, PT_H, SCALE, _font

BG = (22, 17, 11)
TEXT = (243, 233, 214)
MUTED = (161, 149, 130)
MARGIN, HEAD, GAP, RADIUS = 16, 72, 12, 6          # points
CACHE = pathlib.Path(os.environ["LOCALAPPDATA"]) / "User Name" / "app.strunika.mobile" / "Cache" / "export"
PAGES = {"uk": ("сторінка", "сторінки", "сторінок"), "en": ("page", "pages", "pages")}


def plural(n, forms):
    one, few, many = forms
    if n % 10 == 1 and n % 100 != 11: return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14: return few
    return many


def main(lang, name, src=None):
    import pypdfium2 as pdfium
    if src is None:
        pdfs = sorted(CACHE.glob("*.pdf"), key=lambda p: p.stat().st_mtime)
        if not pdfs: sys.exit(f"No PDF in {CACHE}")
        src = pdfs[-1]
    src = pathlib.Path(src)
    keep = ROOT / "shots" / "pdf" / lang / f"{name}.pdf"
    keep.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, keep)

    doc = pdfium.PdfDocument(str(keep))
    s = SCALE
    W, H = PT_W * s, PT_H * s
    frame = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(frame)

    title = src.stem
    f_title, f_sub = _font(17 * s), _font(13 * s)
    while d.textlength(title, font=f_title) > (PT_W - 2 * MARGIN) * s and len(title) > 4:
        title = title[:-2].rstrip() + "…"
    d.text((W / 2, 20 * s), title, font=f_title, fill=TEXT, anchor="mm")
    n = len(doc)
    d.text((W / 2, 42 * s), f"PDF · {n} {plural(n, PAGES[lang])}", font=f_sub, fill=MUTED, anchor="mm")

    page_w = (PT_W - 2 * MARGIN) * s
    y = HEAD * s
    for i in range(n):
        if y >= H: break
        page = doc[i]
        pw, ph = page.get_size()
        scale = page_w / pw
        img = page.render(scale=scale).to_pil().convert("RGB")
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.width - 1, img.height - 1], RADIUS * s, fill=255)
        frame.paste(img, (MARGIN * s, int(y)), mask)
        y += img.height + GAP * s

    out = RAW / lang / f"{name}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.save(out, optimize=True)
    print(f"{keep.relative_to(ROOT)} ({n} pages) -> {out.relative_to(ROOT)} {frame.size}")


if __name__ == "__main__":
    if len(sys.argv) < 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
