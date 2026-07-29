# What the Unbounce Classic editor exposes

**Why this file exists:** what the editor exposes is ground truth for what the file can
legitimately express. If a field is reachable in the UI, it is safe to write; if it isn't,
either the file supports something the UI can't reach (fine — that's the advantage we're
exploiting) or we're about to invent a field Unbounce will silently repair on save.

> ⚠️ **`documentation.unbounce.com` returns 403 to automated fetchers.** Do not burn a
> session trying to scrape it — paste the relevant article text in below by hand.
> `learn.unbounce.com` does fetch. Sources worth pasting:
> - [Using Section Grids and the Snap-To-Grid Function](https://documentation.unbounce.com/hc/en-us/articles/36828041441940-Using-Section-Grids-and-the-Snap-To-Grid-Function)
> - [Understanding the Classic Builder Interface](https://documentation.unbounce.com/hc/en-us/articles/4405901031828-Understanding-the-Classic-Builder-Interface)
> - [Downloading or Uploading an Unbounce Page](https://documentation.unbounce.com/hc/en-us/articles/360000987863)
> - [Classic Builder tutorials](https://learn.unbounce.com/classic-builder-tutorials/)

## Confirmed by direct observation

### Element palette
Section · Box · Text · Image · Button · Lightbox · Form · Video · Custom HTML, plus
per-page **Stylesheets** and **Javascripts** panels. This roster identifies the builder as
**Classic** — which matters because download/upload exists only in Classic.

### Section tab
- `columns` settable **1–50**
- padding **0–200px** per side (default T56 R80 B56 L80)
- `rowHeight`, `xGap`, `yGap` — **separately configurable per breakpoint**
- section **height** (width is not settable) and **"gap below"** (= `geometry.margin.bottom`)
- `snapToGrid` per section; `showGrid` is page-level

### Breakpoints
Desktop + mobile share one element tree. Editing text changes both; positioning can differ
(Cmd-drag moves one breakpoint only). Mobile canvas is **hard-capped at 320px** — the file
cannot exceed the UI here. The tablet breakpoint is disabled by default.

### Grouping
Dragging an element into a box groups them. "Center to bounding box" is available and just
computes a static offset. Snapping works on all four sides of a box.
⚠️ Re-parenting in the mobile view rebases only the mobile offsets — the cmd-key warning is
Unbounce flagging exactly this. Generated files must rebase both breakpoints.

### Fonts and colour
The Google Fonts picker is built in, and custom fonts are supported via `@font-face` with
self-hosted files. **The file format is more capable than the pickers** — arbitrary hex and
any Google Font are expressible in element JSON regardless of what the picker offers. That
gap is the reason for generating the file. For a face that is neither a Google Font nor
self-hosted, see *External fonts* below — proven, and it needs no editor setup.

### Dynamic text replacement
`{KeyWord:Default}` PPC insertion is native in Classic. Relevant for ad-group message
match; it is plain text in the element HTML, so nothing special is needed to emit it. Note it
personalises page **copy** only — it does not write into the lead record. Capturing a URL
parameter *into the lead* is a hidden field plus a domain-level script.

### Icons
- **Inline SVG in a small `lp-code` element renders correctly live.** Confirmed 2026-07-28.
  This is the supported route for icons and the sanctioned use of `lp-code`: one small element
  per icon, never a page-shaped blob.
- **Icon fonts from an external CDN work.** Proven 2026-07-29 (P5). Put the stylesheet
  `<link>` in one `lp-code` element and the glyph markup wherever you want it — see *External
  fonts* below for the recipe. An icon *set* preference (Font Awesome, Lucide…) is a
  per-client convention, so it belongs in the client-setup template, not here.
- **Prefer inline SVG anyway** unless the client has already standardised on an icon font.
  SVG has no network dependency, no FOUT and no licence question; the icon-font route exists
  because some clients arrive with one, not because it is better.

### External fonts (icon fonts and text faces)

**Proven 2026-07-29 (P5), on a real upload, both breakpoints.** A stylesheet `<link>` inside
an `lp-code` element survives import and loads live, and its CSS is **document-global** — one
`<link>` in one small `lp-code` covers the whole page. Everything downstream then works:

- **Glyphs in any other `lp-code`** with no `<link>` of their own. Confirmed.
- **A native `lp-pom-text` element in the external family.** Confirmed — Unbounce does *not*
  strip a `font-family` that appears in no `fonts[]` entry. So non-Google brand faces are
  reachable on real editable text, not just inside code blocks.

```html
<!-- one small lp-code, anywhere on the page, carries the links for the whole document -->
<div id="fonts" data-lp-type="code" style="left:70px;top:0;width:36px;height:12px"
  ><link rel="stylesheet" href="https://cdn.example/icons.css"
  ><link rel="stylesheet" href="https://cdn.example/brand-face.css"></div>
```

⚠️ **Quote a family name whose words are not valid CSS identifiers.** `font-family:Open Sans`
is legal unquoted (two identifiers); `font-family:Press Start 2P` is **invalid CSS** because
`2P` starts with a digit, so the browser drops the whole declaration and the text silently
falls back. The transcriber passes `content.text` through verbatim and does not fix this for
you. Write `font-family:'Press Start 2P'` — quoting always works, so quote when in doubt. This
cost one wasted probe upload; don't repeat it.

**`webFontsExternalInUse` is a real key, and not the one you want.** It is the page-level
record of fonts registered through the editor's own **Settings → Add custom fonts** (family
name + weight + externally hosted URL + a licence acknowledgement; multiple weights per
family). That is an account-admin action, its in-file shape is unproven, and the `lp-code`
`<link>` route above needs none of it — so the transcriber keeps emitting `{}`, which is
correct. Both real exports carry `{}`, including the one using two Google families (those land
in `webFontsInUse`). If a client has already registered custom fonts in the editor and wants
them picked up natively, that is a probe, not a guess.

## What we deliberately don't touch

| Editor feature | Why not |
|---|---|
| Lightbox | `hasLightbox: true` with no lightbox data collapses the **live** mobile layout to desktop. Supporting it means generating sub-page trees *and* getting the flag right. Use an anchor or a second page. |
| Video | Appears in the blank-template sampler but in no real export — untested code path. Use an `lp-code` embed. |
| `<select>` / `<textarea>` form fields | No verified in-file shape. Add natively in the editor after import. |
| Sticky header | No proven key in any export we have. Toggle it in the editor. |
| Editor-registered custom fonts (`webFontsExternalInUse`) | In-file shape unproven, and an account-admin action to set up. The `lp-code` `<link>` route needs none of it — see *External fonts* above. |

**A note on the form-confirmation sub-page.** A real export carries a `sub_pages/` tree — the
form's modal confirmation — while `hasLightbox` is still `false`. So a sub-page tree does not
by itself require the flag, and the transcriber emits exactly one sub-page (the form
confirmation) with the flag off. That combination is proven; `hasLightbox: true` is not.

**There is no account-level lightbox.** Checked against Unbounce's own documentation
2026-07-29: lightboxes are per-page constructs, designed inside the page that owns them (up
to 20 per page). A brand-global, class-triggered promo dialog is therefore a **Script
Manager** (domain-level) script carrying the dialog's HTML/CSS/JS and a click listener for
the agreed class — no `hasLightbox`, no sub-page tree, so the render-breaker above never
comes into play. Whether such a script executes on a *preview* URL is untested; proving it
live needs the client's domain (SPEC-v2 P2, Phase C). Until then, treat a lightbox CTA as
an anchor and say so in the handover. Don't set the flag to find out: `true` without a
lightbox tree is the render-breaker above.

## After every upload

1. The page arrives **unpublished** and often in **"weighted" (A/B) routing mode** even as a
   single variant — reset traffic mode.
2. Check a **real phone**, not just the editor's mobile preview. The editor is tolerant of
   the three render-breakers in `skills/build-page/references/format.md`; a real device is not.
3. Add whatever was deliberately left to the editor (dropdowns, sticky header, real embed
   snippets, legal disclaimer).
