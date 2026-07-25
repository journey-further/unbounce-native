// Measure a design HTML file in a real browser and report what the design skill needs
// to finish it: true wrapped text heights, image natural sizes, and overflow flags.
//
//   node measure.mjs design.html [desktop|mobile] [shot.png]
//
// Why a browser: Unbounce Classic is absolute-positioned at BOTH breakpoints (no reflow),
// so an absolutely-positioned HTML page with the same Google Fonts wraps identically to
// Unbounce. Heights are measured, never estimated. Needs node + Chromium + network
// (Google Fonts must actually load or the metrics are wrong). The transcriber does not.
//
// Output is a JSON report on stdout. Nothing is written to disk except an optional
// screenshot — the numbers go back into the design HTML by hand, so the design file
// stays the single source of truth.
import { chromium } from 'playwright';

const [file, bp = 'desktop', shot] = process.argv.slice(2);
if (!file) { console.error('usage: node measure.mjs design.html [desktop|mobile] [shot.png]'); process.exit(2); }
const WIDTH = bp === 'mobile' ? 320 : 1280;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: WIDTH, height: 900 }, deviceScaleFactor: 2 });
const url = 'file://' + (file.startsWith('/') ? file : process.cwd() + '/' + file);
await page.goto(url, { waitUntil: 'networkidle' });
await page.evaluate(() => document.fonts.ready);

const report = await page.evaluate((bp) => {
  const out = { text: {}, images: {}, overflow: [], sections: {} };

  // ⚠️ scrollHeight is max(content, clientHeight) — a declared height FLOORS it, so reading
  // it directly can only ever confirm the number you already wrote. Measure with the height
  // released, then put it back. (An earlier tool floored measurements this way via
  // min-height and ran a whole page ~35% too tall.)
  // ...and the release has to be !important itself, or the mobile block (which is required
  // to be !important) wins and we measure the declared height right back again.
  const contentHeight = (el) => {
    const had = el.style.getPropertyValue('height'), pri = el.style.getPropertyPriority('height');
    el.style.setProperty('height', 'auto', 'important');
    const h = Math.ceil(el.getBoundingClientRect().height);
    el.style.removeProperty('height');
    if (had) el.style.setProperty('height', had, pri);
    return h;
  };

  for (const el of document.querySelectorAll('[data-lp-type="text"]')) out.text[el.id] = contentHeight(el);
  for (const el of document.querySelectorAll('[data-lp-type="image"]')) {
    out.images[el.id] = `${el.naturalWidth}x${el.naturalHeight}`;
    if (!el.naturalWidth) out.overflow.push({ id: el.id, axis: 'asset', box: 0, content: 0, text: 'image failed to load: ' + el.getAttribute('src') });
  }
  for (const el of document.querySelectorAll('section[data-lp-type="block"]')) {
    let bottom = 0;
    for (const k of el.children) bottom = Math.max(bottom, k.offsetTop + k.offsetHeight);
    out.sections[el.id] = { declared: el.offsetHeight, contentBottom: bottom };
    // blocks stack, so content below a section's height lands on top of the next section
    if (bottom > el.offsetHeight + 2)
      out.overflow.push({ id: el.id, axis: 'section', box: el.offsetHeight, content: bottom,
                          text: 'content spills past the section height' });
  }
  for (const el of document.querySelectorAll('[data-lp-type]')) {
    if (el.dataset.lpType === 'block') continue;
    const box = el.getBoundingClientRect();
    // images are deliberately cropped to their box by object-fit, so releasing the height
    // just reports their aspect ratio — not an overflow
    const ch = el.dataset.lpType === 'image' ? 0 : contentHeight(el);
    if (ch > Math.ceil(box.height) + 2)
      out.overflow.push({ id: el.id, axis: 'height', box: Math.round(box.height), content: ch,
                          text: (el.innerText || '').trim().slice(0, 48) });
    // an unbreakable word (a long ALL-CAPS heading) runs off the column instead of wrapping
    if (el.scrollWidth > Math.ceil(box.width) + 2)
      out.overflow.push({ id: el.id, axis: 'width', box: Math.round(box.width), content: el.scrollWidth,
                          text: (el.innerText || '').trim().slice(0, 48) });
  }
  // Is the mobile block actually winning? An inline style attribute outranks any stylesheet
  // rule regardless of media query, so one missing !important renders DESKTOP geometry at
  // 320px — a silently wrong preview, which is worse than a broken one.
  if (bp === 'mobile') {
    for (const sheet of document.styleSheets) {
      let rules; try { rules = sheet.cssRules; } catch { continue; }
      for (const media of rules) {
        if (!(media instanceof CSSMediaRule)) continue;
        for (const rule of media.cssRules) {
          let el; try { el = document.querySelector(rule.selectorText); } catch { continue; }
          if (!el || !el.dataset.lpType) continue;
          const box = el.getBoundingClientRect(), cs = getComputedStyle(el);
          for (const prop of rule.style) {
            const want = rule.style.getPropertyValue(prop);
            const got = prop === 'width' ? box.width : prop === 'height' ? box.height
                      : prop === 'display' ? cs.display : parseFloat(cs[prop]);
            const ok = prop === 'display' ? want.trim() === got
                     : Math.abs(parseFloat(want) - got) < 1.5;
            if (!ok) out.overflow.push({ id: el.id, axis: 'override', box: want, content: got,
              text: `mobile ${prop} is not being applied — add !important` });
          }
        }
      }
    }
  }

  const doc = document.documentElement;
  out.pageWidth = Math.max(doc.scrollWidth, document.body.scrollWidth);
  return out;
}, bp);

if (shot) await page.screenshot({ path: shot, fullPage: true });
await browser.close();

report.breakpoint = bp;
report.viewport = WIDTH;
if (report.pageWidth > WIDTH) report.overflow.push({ id: '(page)', axis: 'width', box: WIDTH, content: report.pageWidth });
console.log(JSON.stringify(report, null, 1));
if (report.overflow.length) {
  console.error(`\n${report.overflow.length} overflow(s) at ${bp} — fix the design, do not transcribe:`);
  for (const o of report.overflow) console.error(`  ${o.id} ${o.axis}: box ${o.box} < content ${o.content}  "${o.text || ''}"`);
  process.exit(1);
}
