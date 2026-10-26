# strunika.com

Static landing page for Strunika. No bundler, no framework: `index.html` (English), `ua/index.html` (Ukrainian), `en/index.html` (a redirect to `/` for old links), `privacy.html`, `assets/`.

## Edit → build → deploy

1. Edit the HTML. FAQ entries are plain `<details><summary>Q</summary><div class="a"><p>A</p></div></details>` blocks.
2. `python tools/build.py` regenerates the FAQPage JSON-LD in both pages from those blocks and rewrites `sitemap.xml`.
3. Commit and push `main`. GitHub Pages serves the root of the branch (Settings → Pages → Deploy from a branch → `main` / `/ (root)`). No Actions minutes are used.

## Domains

- `CNAME` holds `strunika.com`. At the registrar: `A` records for `strunika.com` → 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153 and `CNAME www` → `<github-user>.github.io`. Then tick "Enforce HTTPS" in the Pages settings.
- `strunika.app` is the App Store short link: a second Pages repo (`../strunika-app-redirect`) with its own `CNAME` and a redirect page. `.app` is HSTS-preloaded, so the redirect must be served over HTTPS; a registrar-level HTTP forward will not work.

## Local preview

Open `index.html` in a browser, or `python -m http.server 8080` from this folder.
