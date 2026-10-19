"""Build step for the static site (no bundler):
 - injects a FAQPage JSON-LD block into every page between <!--FAQ-LD--> markers,
   generated from the page's own <details>/<summary> elements, so the HTML and the
   structured data can never drift apart;
 - writes sitemap.xml with the current date.
Run from the site root:  python tools/build.py
"""
import html, json, re, sys, datetime, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = {"index.html": "https://strunika.com/", "en/index.html": "https://strunika.com/en/"}

DETAILS = re.compile(r"<details>\s*<summary>(.*?)</summary>\s*<div class=\"a\">(.*?)</div>\s*</details>", re.S)
TAG = re.compile(r"<[^>]+>")

def text(s: str) -> str:
    s = TAG.sub(" ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()

def faq_ld(page: str) -> str:
    items = [{"@type": "Question", "name": text(q), "acceptedAnswer": {"@type": "Answer", "text": text(a)}}
             for q, a in DETAILS.findall(page)]
    data = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": items}
    body = json.dumps(data, ensure_ascii=False, indent=1)
    return f'<!--FAQ-LD--><script type="application/ld+json">\n{body}\n</script><!--/FAQ-LD-->', len(items)

for rel in PAGES:
    p = ROOT / rel
    src = p.read_text(encoding="utf-8")
    block, n = faq_ld(src)
    out, k = re.subn(r"<!--FAQ-LD-->.*?<!--/FAQ-LD-->", lambda m: block, src, flags=re.S)
    if k != 1:
        sys.exit(f"{rel}: FAQ-LD markers not found")
    p.write_text(out, encoding="utf-8")
    print(f"{rel}: {n} FAQ entries")

today = datetime.date.today().isoformat()
urls = "\n".join(
    f"  <url><loc>{u}</loc><lastmod>{today}</lastmod>"
    f'<xhtml:link rel="alternate" hreflang="uk" href="https://strunika.com/"/>'
    f'<xhtml:link rel="alternate" hreflang="en" href="https://strunika.com/en/"/></url>'
    for u in PAGES.values())
urls += f"\n  <url><loc>https://strunika.com/privacy.html</loc><lastmod>{today}</lastmod></url>"
(ROOT / "sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
    f"{urls}\n</urlset>\n", encoding="utf-8")
print("sitemap.xml written")
