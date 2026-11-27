// Renders scene.html frame-by-frame to JPEGs.
// usage: node render.js <outDir> <w> <h> [start] [end] [step]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const [outDir = 'frames', w = '1080', h = '1920'] = process.argv.slice(2);
  const start = +(process.argv[5] || 0), end = +(process.argv[6] || 900), step = +(process.argv[7] || 1);
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files'] });
  const page = await browser.newPage({ viewport: { width: +w, height: +h } });
  page.on('pageerror', e => console.error('[pageerror]', e.message));
  page.on('console', m => { if (m.type() === 'error') console.error('[console]', m.text()); });
  await page.goto(`file://${path.resolve(__dirname, 'scene.html')}?w=${w}&h=${h}`);
  await page.evaluate(() => window.ready);
  for (let i = start; i < end; i += step) {
    const t0 = Date.now();
    const url = await page.evaluate(i => window.renderFrame(i), i);
    fs.writeFileSync(path.join(outDir, `f${String(i).padStart(4, '0')}.jpg`), Buffer.from(url.split(',')[1], 'base64'));
    if (step > 1 || i % 60 === 0) console.log(`frame ${i} ${Date.now() - t0}ms`);
  }
  await browser.close();
})();
