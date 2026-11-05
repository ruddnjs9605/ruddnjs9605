// Renders index.html frame by frame with Chromium and pipes PNGs into ffmpeg.
// node render.js out.mp4            -> full video
// node render.js - 30,150,400       -> stills only (still_<frame>.png)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');

(async () => {
  const dir = __dirname;
  const out = process.argv[2] || path.join(dir, 'video.mp4');
  const only = process.argv[3];
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(dir, 'index.html'));
  const total = await page.evaluate(() => TOTAL);

  if (only) {
    for (const f of only.split(',').map(Number)) {
      await page.evaluate(f => render(f), f);
      await page.screenshot({ path: path.join(dir, `still_${f}.png`) });
    }
    await browser.close();
    return;
  }

  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', '30', '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let f = 0; f < total; f++) {
    await page.evaluate(f => render(f), f);
    const buf = await page.screenshot({ type: 'png' });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (f % 150 === 0) console.log(`frame ${f}/${total}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();
  console.log('done', out);
})();
