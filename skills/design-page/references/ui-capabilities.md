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
gap is the reason for generating the file.

### Dynamic text replacement
`{KeyWord:Default}` PPC insertion is native in Classic. Relevant for ad-group message
match; it is plain text in the element HTML, so nothing special is needed to emit it. Note it
personalises page **copy** only — it does not write into the lead record. Capturing a URL
parameter *into the lead* is a hidden field plus a domain-level script.

### Icons
- **Inline SVG in a small `lp-code` element renders correctly live.** Confirmed 2026-07-28.
  This is the supported route for icons and the sanctioned use of `lp-code`: one small element
  per icon, never a page-shaped blob.
- **Icon fonts from a non-Google CDN are unproven.** `settings.json` carries a
  `webFontsExternalInUse` key that the transcriber always emits as `{}`; whether it is a real
  hook for an external font CDN or vestigial has not been probed. Until it is, an icon font is
  refused — use SVG. An icon *set* preference (Font Awesome, Lucide…) is a per-client
  convention, so it belongs in the client-setup template, not here.

## What we deliberately don't touch

| Editor feature | Why not |
|---|---|
| Lightbox | `hasLightbox: true` with no lightbox data collapses the **live** mobile layout to desktop. Supporting it means generating sub-page trees *and* getting the flag right. Use an anchor or a second page. |
| Video | Appears in the blank-template sampler but in no real export — untested code path. Use an `lp-code` embed. |
| `<select>` / `<textarea>` form fields | No verified in-file shape. Add natively in the editor after import. |
| Sticky header | No proven key in any export we have. Toggle it in the editor. |
| Icon fonts from an external CDN | `webFontsExternalInUse` unprobed — see Icons above. Use inline SVG. |

**A note on the form-confirmation sub-page.** A real export carries a `sub_pages/` tree — the
form's modal confirmation — while `hasLightbox` is still `false`. So a sub-page tree does not
by itself require the flag, and the transcriber emits exactly one sub-page (the form
confirmation) with the flag off. That combination is proven; `hasLightbox: true` is not.

**Global (account-level) lightboxes are an open question, not a refusal.** Whether a global
dialog triggered by a custom class fires on a page built with `hasLightbox: false` has not
been tested — it needs an account that has global lightboxes available plus a published page
on a real domain. Until then, treat a lightbox CTA as an anchor and say so in the handover.
Don't set the flag to find out: `true` without a lightbox tree is the render-breaker above.

## After every upload

1. The page arrives **unpublished** and often in **"weighted" (A/B) routing mode** even as a
   single variant — reset traffic mode.
2. Check a **real phone**, not just the editor's mobile preview. The editor is tolerant of
   the three render-breakers in `skills/build-page/references/format.md`; a real device is not.
3. Add whatever was deliberately left to the editor (dropdowns, sticky header, real embed
   snippets, legal disclaimer).
