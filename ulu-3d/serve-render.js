// Serves this folder over http (ES modules) and renders scene.html frame-by-frame.
// usage: node serve-render.js <outDir> <w> <h> [start] [end] [step]
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.otf': 'font/otf', '.woff2': 'font/woff2', '.json': 'application/json', '.jpg': 'image/jpeg', '.png': 'image/png' };
const root = __dirname;
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  let fp = u.startsWith('/fonts/sys/') ? path.join('/usr/share/fonts/opentype/inter', path.basename(u)) : path.join(root, u);
  if (!fp.startsWith(root) && !fp.startsWith('/usr/share/fonts/')) { res.writeHead(403); return res.end(); }
  fs.readFile(fp, (e, d) => { if (e) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'Content-Type': MIME[path.extname(fp)] || 'application/octet-stream' }); res.end(d); });
});
(async () => {
  const [outDir = 'frames', w = '1920', h = '1080'] = process.argv.slice(2);
  const start = +(process.argv[5] || 0), end = +(process.argv[6] || 900), step = +(process.argv[7] || 1);
  fs.mkdirSync(outDir, { recursive: true });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const port = server.address().port;
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: +w, height: +h } });
  page.on('pageerror', e => console.error('[pageerror]', e.message));
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.error('[console]', m.text()); });
  await page.goto(`http://127.0.0.1:${port}/scene.html?w=${w}&h=${h}`);
  await page.waitForFunction(() => window.READY === true, null, { timeout: 120000 });
  for (let i = start; i < end; i += step) {
    const fp = path.join(outDir, `f${String(i).padStart(4, '0')}.jpg`);
    if (process.env.RESUME && fs.existsSync(fp) && fs.statSync(fp).size > 10000) continue;
    const t0 = Date.now();
    const url = await page.evaluate(i => window.renderFrame(i), i);
    fs.writeFileSync(fp, Buffer.from(url.split(',')[1], 'base64'));
    if (step > 1 || i % 30 === 0) console.log(`frame ${i} ${Date.now() - t0}ms`);
  }
  await browser.close(); server.close();
})();
