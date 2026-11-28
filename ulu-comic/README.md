# Ulu Comics #1 — landing page (Astro)

English launch site for the Ulu chat app, designed as a printed comic book:
the hero is the cover, each feature is a chapter drawn in panels
(1 Live · 2 Reels · 3 Groups · 4 Stories), plus an interactive "write the next panel"
page, the FAQ as a letters page and the waitlist as a clip-out coupon.

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # static site in dist/ (CSS inlined, fonts self-hosted)
```

## Structure
- `src/pages/index.astro` – the whole issue (content + page styles + tiny inline script)
- `src/components/Kid.astro` – comic characters built from props (skin, hair style, shirt, mood, wave, phone)
- `src/components/Ulu.astro` – the mascot, a speech balloon with legs
- `src/components/Burst.astro` – starbursts (POW!, KA-CHAT!)
- `src/components/Balloon.astro` – speech / shout / thought balloons and caption boxes
- `public/fonts/` – Dela Gothic One, Shantell Sans, Space Mono (SIL OFL)

No JS framework, no client bundle: everything is static HTML/CSS/SVG with ~3 KB of inline JS.
Respects `prefers-reduced-motion`, keyboard focus, and works down to 320 px.

## Before launch
- Replace the App Store / Google Play links (`data-soon` buttons in the cover).
- Wire the coupon form (`// TODO` in the inline script) to your mailing-list provider.
- Footer Privacy / Terms links.
