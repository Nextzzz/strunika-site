"""WebP copies of the screenshots: six times smaller than the PNGs the capture
tool writes, so a phone on mobile data gets them before they scroll into view.
Run after new screenshots land in assets/screens/<lang>/; the pages reference
both (<picture>: webp first, png as the fallback)."""
import pathlib
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
for png in sorted((ROOT / "assets/screens").rglob("*.png")):
    webp = png.with_suffix(".webp")
    if webp.exists() and webp.stat().st_mtime >= png.stat().st_mtime:
        continue
    Image.open(png).save(webp, "WEBP", quality=82, method=6)
    print(f"{png.relative_to(ROOT).as_posix()}: {png.stat().st_size // 1024} KB -> {webp.stat().st_size // 1024} KB")
