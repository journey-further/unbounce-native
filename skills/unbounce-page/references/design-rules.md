# The design contract

The design HTML is a real, renderable, semantic HTML file. It is **the review artifact and
the build input at once** — absolutely positioned with the same Google Fonts as the live
page, so what a browser shows is what Unbounce will show. Iterate at browser speed; the
`.unbounce` render is verification, not the preview.

**Each fact lives in exactly one place.** That is the rule the whole contract follows.

| Fact | Where it lives |
|---|---|
| Desktop geometry | inline `style` on the element |
| Mobile geometry | one `<style>` block, `@media (max-width:600px)`, one rule per id |
| Hide on mobile | `display:none !important` in that media block |
| Nesting / grouping | the DOM tree |
| Element type | `data-lp-type` |
| Image crop mode | `data-fit="cover\|contain"` |
| Image natural size | `data-nat="WIDTHxHEIGHT"` |
| Fonts | the Google Fonts `<link>` href |
| Page colours | `data-*` on `<body>` |
| Copy, colour, type | inline CSS inside the text element's HTML |

## Skeleton

```html
<!doctype html>
<html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;700&family=Open+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  /* design-time only — not shipped; Unbounce handles breakpoints natively */
  body { position:relative; width:1280px; margin:0; font-family:'Open Sans',sans-serif; }
  section { position:relative; width:1280px; overflow:hidden; }
  [data-lp-type] { position:absolute; box-sizing:border-box; }
  [data-lp-type="text"] p { margin:0; }
  @media (max-width:600px) {
    body, section { width:320px; }
    #hero-h1 { left:10px; top:36px; width:300px; height:212px !important; }
    #hero-phone { display:none !important; }
  }
</style></head>
<body data-accent="#99cc00" data-ink="#1d2327" data-bg="#ffffff">

<section id="s-hero" data-lp-type="block" data-name="Hero" style="height:720px;background:#1d2327">
  <img id="hero-bg" data-lp-type="image" data-fit="cover" data-nat="2189x1642" src="assets/roof.webp"
       style="left:0;top:0;width:1280px;height:720px">
  <div id="hero-h1" data-lp-type="text" style="left:70px;top:96px;width:564px;height:132px">
    <p><span style="font-family:Oswald;font-size:52px;font-weight:700;color:#ffffff;line-height:1.08">UP TO $2,500 OFF</span></p>
  </div>
  <div id="hero-card" data-lp-type="box" data-name="Form card"
       style="left:694px;top:48px;width:516px;height:588px;background:#ffffff;border-radius:8px;box-shadow:0 12px 34px rgba(0,0,0,.22)">
    <form id="hero-form" data-lp-type="form" data-confirm="Thanks — we'll follow up within 24 hours."
          style="left:36px;top:24px;width:444px;height:432px">
      <input type="text"  name="first_name" placeholder="First name" data-label="First Name" required>
      <input type="email" name="email"      placeholder="Email"      data-label="Email" required>
      <input type="tel"   name="phone"      placeholder="Phone"      data-label="Phone Number" required>
      <button id="hero-submit" data-lp-type="submit"
              style="left:0;top:380px;width:444px;height:52px;background:#99cc00;color:#1d2327;border-radius:6px;font-family:Oswald;font-size:16px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px">Get my free estimate</button>
    </form>
  </div>
  <a id="hero-cta" data-lp-type="button" href="#hero-form"
     style="left:70px;top:600px;width:180px;height:48px;background:#99cc00;color:#1d2327;border-radius:6px">Get a free estimate</a>
</section>

</body></html>
```

## `data-lp-type`

The one thing CSS cannot express. `block` · `box` · `text` · `image` · `button` · `form` ·
`submit` · `code`. Anything without it is an untracked wrapper and is ignored — so don't
create any.

- **`block`** — a `<section>`, top level only, no `left`/`top` (blocks stack). Needs
  `height` and a background. `data-name` becomes the section's name in the editor; give
  every block one, the client sees it.
- **`box`** — cards, overlays, dividers, accent strips, badges. `background`, `opacity`,
  `border-radius`, `border`, `box-shadow` are all read.
- **`text`** — inner HTML ships verbatim into `content.text`. Style it with inline spans;
  that is what makes arbitrary colours and fonts work and keeps it client-editable.
- **`image`** — an `<img>`. `data-fit="cover"` for backgrounds and cropped photos,
  `"contain"` for logos. `data-nat` is required (see below). An `href` makes it clickable.
- **`button`** — an `<a>` or `<button>`. Inner text is the label. `href="#some-id"` becomes
  an in-page anchor, `href="tel:…"` a call link. Styling comes from inline CSS; add
  `--hover:#88b800` for an explicit hover colour, otherwise it is derived by darkening.
- **`form`** — a real `<form>`. See below.
- **`submit`** — the form's submit button, **a child of the `<form>`**, positioned relative
  to it.
- **`code`** — inner HTML ships as Custom HTML. Embeds, decorative SVG, third-party
  widgets. Never contains the literal string `<head>`.

## Geometry

**Desktop geometry is inline CSS**: `left`, `top`, `width`, `height` in px. The browser
renders from it and the transcriber reads the same values — one fact, one place. Grid
conformance is *derived* from `left`/`width`, so there is no `data-grid-col`.

Use absolute positioning, never flexbox or grid. That is the point of designing tight to
spec, and the browser renders it identically either way.

**Mobile geometry is one `@media (max-width:600px)` block**, one rule per element id, one
declaration per line, **every declaration `!important`**.

⚠️ **The `!important` is load-bearing, not stylistic.** An inline `style` attribute outranks
any stylesheet rule regardless of media query, so without it the browser renders the
*desktop* geometry at 320px and the mobile preview is silently wrong.

The media block has a **pinned grammar** so a stdlib parser reads it without a CSS engine:
`#id { … }`, one declaration per line, and a fixed whitelist — `left`, `top`, `width`,
`height`, `display`. Anything else is a validator error, not a parse fallback.

**Every positioned element needs a mobile rule** (geometry, or `display:none`). No rule is
an error, not a silent inherit — mobile intent must be explicit.

**Hide-on-mobile is `display:none !important`**, not a data attribute. It has to be real CSS
anyway, or hidden elements still render in the 320px preview and pollute the measured stack.
The transcriber reads it and emits `breakpoints.mobile.geometry.visible: false`.

## The form

A real `<form>` with real inputs, mapped mechanically:

| HTML | → Unbounce |
|---|---|
| `<input type="text">` | `lpType: single-line-text` |
| `<input type="email">` | `+ validations.email: true` |
| `<input type="tel">` | `+ validations.phone: true`, `validationType: "north-american"` |
| `required` | `validations.required` |
| `name` | field `id` |
| `placeholder` | `placeholder` |
| `data-label` | the visible field label (falls back to `placeholder`, then `name`) |
| `data-confirm` on the `<form>` | the modal confirmation message |

**`<select>` and `<textarea>` are a hard error.** Their in-file shape appears in no real
export, so the transcriber refuses rather than guessing — add those fields natively in the
editor after import.

**Style the design form to Unbounce's real chrome or the measurement lies.** Unbounce lays
fields out on a **71px stride** — 15px label, 4px gap, 34px input inside a 53px container.
Everything below the form stacks from its measured height, so an inaccurate form
propagates error down the whole page. Put this in the design-time `<style>`:

```css
form[data-lp-type="form"] input { position:absolute; left:0; width:100%; height:34px; margin:0;
  box-sizing:border-box; border:1px solid #d6d6d2; border-radius:6px; background:#fafafa;
  font:14px 'Open Sans',sans-serif; padding:0 10px; }
form[data-lp-type="form"] input:nth-of-type(1){ top:19px }
form[data-lp-type="form"] input:nth-of-type(2){ top:90px }
form[data-lp-type="form"] input:nth-of-type(3){ top:161px }   /* +71 per field */
```

⚠️ Measured form height is **close, not exact** — this approximates Unbounce's own chrome.
Tracked in `BACKLOG.md`; extract the real published markup when it starts to matter.

## Fonts

Derived automatically from the Google Fonts `<link>` href → `settings.json` `fonts[]` +
`webFontsInUse`. Declare exactly the families and weights the design uses; anything you
reference in an inline style but don't declare renders as a fallback.

## Measurement

Heights are **measured, never estimated**:

```bash
node scripts/measure.mjs design.html desktop
node scripts/measure.mjs design.html mobile shot-mobile.png
```

It reports, per breakpoint: true wrapped `scrollHeight` for every text element, every
image's `naturalWidth`/`naturalHeight`, each section's declared vs content-bottom height,
and any element whose content overflows its declared box. **Write those numbers back into
the design HTML.** The design file carries derived numbers, which makes it a build artifact
of the design step — regenerate it when copy changes rather than hand-patching.

Needs node + Chromium + network (Google Fonts must actually load or the metrics are wrong).
The transcriber needs none of that.

⚠️ **Never put `min-height` on a text element.** It floors `scrollHeight` at whatever you
already declared, so heights can only grow and every over-estimate survives forever — a
page ran ~35% taller than Unbounce's own text heights because of exactly this.

**Overflow is a design bug, not a transcription problem.** `measure.mjs` exits non-zero;
fix the design.

⚠️ **Unbounce's Oswald renders wider than Chrome's Google-Fonts Oswald.** A long unbreakable
word (`REPLACEMENT.`) can measure as fitting and still run off the column live. Leave
display headings ~5% of slack on width, or break them with an explicit `<br>`.

## Faithful-build discipline

The design is the source of truth for the build; the *brief* is the source of truth for the
design. Between them nothing gets invented.

- **Extract exact values from the source — never eyeball a screenshot.** Every hex,
  font-family/size/weight/line-height, image, dimension, gap and copy string comes from the
  source. Screenshots are for layout intent and final side-by-side QA only.
- **Copy is verbatim.** No tightening, no paraphrase, unless a copy change is explicit.
- **Preserve counts.** N cards in the brief → N cards in the build. The canonical failure is
  inventing a 6th card because "3×2 looks neater".
- **Preserve every form field, validation rule and field order.** Order is a UX decision.
- **Reuse assets, never substitute.**
- **Replicate interaction states** — `:hover`/`:focus`, not just the resting state.
- **Section backgrounds bleed full-width; content stays inside the 1140 column.**
- **No un-sourced additions.** Before adding any element, point at the thing in the brief
  that creates it. Don't promote a logo-in-a-row into a sticky header because the pattern
  feels familiar.
- **Element names are not copy.** "Nav Bar – Desktop" is a layer name.

### Structural rules that come from the platform

- **Exactly one form.** Every other CTA anchors to it (`href="#the-form-id"`).
- **No navigation.** No header nav, no footer link lists. Every outbound link is an exit.
  The only acceptable links are the CTA anchors and inconspicuous legal links.
- **A card should be one group.** Put a card's contents inside its box element so the client
  drags, duplicates and moves the card as one unit. This is the native-editability goal, and
  it collapses the mobile layout to positioning ~10 cards instead of ~115 elements.

## Mobile layout rules

Derived from diffing a hand-tuned export against a generated one — the "last mile"
decomposes into rules, not taste:

- **Full column width, no proportional scaling.** Cards, forms and reviews go to the full
  300px; a box and the elements inside it re-stack internally.
- **Vertical rhythm = true content height + 20–28px air.** ~24px between block-level units,
  ~20px between and below card children. Tighter gaps only *look* right against bloated
  height estimates.
- **A header is one row, not a stack.** If a block's few children (≤3, none of them text,
  each ≤60px tall) fit side by side in 300px, keep them on one row — first left, last right.
  Stacking a 2-element header wastes half the block.
- **Standalone CTAs centre in the column** and keep their width: `left = (300 − w)/2 + 10`.
  Never left-aligned, never stretched.
- **Hiding beats cramming.** Decorative flourishes, duplicate phone numbers already covered
  by a CTA, and empty placeholders should be `display:none`. This is the biggest single
  lever on mobile quality, and it is editorial — a human decision, not a derived one.
- **Big display headings are tall on mobile** and that is fine. A 52px heading in a 300px
  column wraps to ~4 lines and reads as a bold hero. Inline font-size is shared across
  breakpoints, so a mobile-only size isn't expressible — if a tighter look is wanted, the
  client drops the font size in the editor.
