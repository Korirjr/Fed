# Ulu — landing page

Arabic (RTL), cartoon-style launch site for the Ulu chat app: Live · Reels · Groups · Stories.

- Single file `index.html`, zero dependencies, no build step. Fonts: Readex Pro (SIL OFL) in `fonts/`.
- Interactive phone demo (Stories / Reels / Live / Groups), live hero chat, animated mascot whose eyes follow the cursor.
- Light/dark mode, responsive down to 320 px, keyboard-accessible tabs (arrow keys), `prefers-reduced-motion`, SEO + Open Graph + JSON-LD.

## Run locally
```bash
cd ulu-site && python3 -m http.server 8000   # open http://localhost:8000
```
(Opening the file directly with file:// blocks the web fonts — use a server.)

## Before launch
- Store links: replace `href="#"` on `.store` buttons (and remove the "coming soon" toast in the script).
- Email form: wire the `// TODO` in the `#notify` submit handler to your mailing-list backend.
- Add `og-cover.jpg` (1200×630) — `../ulu-ad/cover-16x9.jpg` works as a start.
- Social / legal links in the footer.
