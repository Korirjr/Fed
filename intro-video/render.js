// Renders scene.html frame-by-frame to JPEGs.
// usage: node render.js <outDir> [start] [end] [step]
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const outDir = process.argv[2] || 'frames';
  const start = +(process.argv[3] || 0), end = +(process.argv[4] || 540), step = +(process.argv[5] || 1);
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files'] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  page.on('console', m => console.log('[page]', m.text()));
  page.on('pageerror', e => console.error('[pageerror]', e.message));
  await page.goto('file://' + path.resolve(__dirname, 'scene.html'));
  await page.evaluate(() => window.ready);
  for (let i = start; i < end; i += step) {
    const t0 = Date.now();
    const url = await page.evaluate(i => window.renderFrame(i), i);
    fs.writeFileSync(path.join(outDir, `f${String(i).padStart(4, '0')}.jpg`), Buffer.from(url.split(',')[1], 'base64'));
    if (i % 30 === 0 || step > 1) console.log(`frame ${i} ${Date.now() - t0}ms`);
  }
  await browser.close();
})();
