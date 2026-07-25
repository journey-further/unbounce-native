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
match; it is plain text in the element HTML, so nothing special is needed to emit it.

## What we deliberately don't touch

| Editor feature | Why not |
|---|---|
| Lightbox | `hasLightbox: true` with no lightbox data collapses the **live** mobile layout to desktop. Supporting it means generating sub-page trees *and* getting the flag right. Use an anchor or a second page. |
| Video | Appears in the blank-template sampler but in no real export — untested code path. Use an `lp-code` embed. |
| `<select>` / `<textarea>` form fields | No verified in-file shape. Add natively in the editor after import. |
| Sticky header | No proven key in any export we have. Toggle it in the editor. |

## After every upload

1. The page arrives **unpublished** and often in **"weighted" (A/B) routing mode** even as a
   single variant — reset traffic mode.
2. Check a **real phone**, not just the editor's mobile preview. The editor is tolerant of
   the three render-breakers in `format.md`; a real device is not.
3. Add whatever was deliberately left to the editor (dropdowns, sticky header, real embed
   snippets, legal disclaimer).
