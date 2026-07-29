---
name: build-page
description: Turn a measured Unbounce design HTML file into an importable .unbounce archive of native lp-pom-* elements, and report what to do after upload. Mechanical — it validates and refuses rather than adjusting the design. Use when asked to build, transcribe, package or generate the .unbounce file from a design.html, or when a page imports but renders wrong.
---

# Build the .unbounce file

`design.html` in, `out.unbounce` out. Mechanical, stdlib-only, no network, no design
conversation.

You do not need to have designed the page, and usually you didn't. Everything you need is in
the file: inline geometry, the `@media (max-width:600px)` block, measured heights, a Google
Fonts `<link>`, `data-nat` on every image.

## The one thing that matters

Real native `lp-pom-*` elements, so the client's team can edit the page in the drag-and-drop
editor. A page-shaped `lp-code` element imports fine, looks right, and is dead to the editor —
that is the failure this skill exists to avoid.

## Do this

**1 · Check the design is finished.** It needs the Google Fonts `<link>`, `data-nat` on every
image, a mobile rule for every positioned element, and measured heights. If measurement
hasn't run, run it — `node skills/design-page/scripts/measure.mjs design.html desktop` and
`… mobile`. **Overflow is a stop.** Report it and don't transcribe.

**2 · Transcribe.**

```bash
python3 scripts/transcribe.py design.html out.unbounce \
    --page-name "The page name the client will see"
```

Stdlib only, single pass, no network. It validates and **writes nothing when there are
errors** — so it is also a free dry-run at any point.

**3 · Resolve errors in the design, never in the transcriber.** Every validator error names
an element and a reason. The fix is in the markup: nudge the element onto a column line,
shorten a width, add the missing mobile rule. Width warnings (`not a whole span`) are
advisory — fix them if the design intends to tile, leave them if the width is deliberate.

A validation failure is reported back as **"the design is wrong, here is where"**. Do not
open a design conversation and do not fix it in place: that is `design-page`'s job, and the
handoff back is cheap.

**4 · Verify the archive** before handing it over:

```bash
tar tf out.unbounce | head -30
python3 - <<'PY'
import json, tarfile
t = tarfile.open("out.unbounce")
s = json.load(t.extractfile(next(n for n in t.getnames()
     if n.endswith("a/settings.json") and "sub_pages" not in n)))
assert s["multipleBreakpointsEnabled"] is True and s["hasLightbox"] is False
els = json.load(t.extractfile(next(n for n in t.getnames() if n.endswith("a/elements.json"))))
assert not [e for e in els if isinstance(
     (e.get("breakpoints",{}).get("mobile",{}).get("geometry") or {}).get("scale"), str)]
print(len(els), "elements, flags OK")
PY
```

**5 · Report.** Short and actionable:

- element count, and which sections became which blocks
- any remaining width warnings
- **upload steps:** All Pages → "Upload an Unbounce Page" → one file, async, email confirms.
  It arrives **unpublished** and often in **"weighted" A/B routing** even as a single
  variant — reset traffic mode. `upload-page` automates all of this; these are the manual
  steps for when the file is being handed to someone rather than uploaded.
- **check a real phone**, not the editor's mobile preview — the editor is tolerant of
  render-breakers a real device is not
- a **"Not in the file"** section: every target feature deliberately not expressed — refused
  primitives, unsupported CSS, dropped decoration, editor-only behaviours, placeholder
  furniture shipped as-is, and any documented flow step done another way. If something wasn't
  built, it goes in this list. A silent omission is the failure mode this section exists to
  prevent.

## Hard rules

1. **Native elements only, per element.** Twenty 32px icon `lp-code` embeds are fine; one
   900px-tall one is the failure. Never a page-shaped blob.
2. **Nine primitives:** `root` `block` `box` `text` `image` `button` `form` `lp-code`
   `lp-stylesheet`. One form per page (Classic hard limit).
3. **The transcriber never moves anything.** Off-grid or off-canvas geometry is a design
   error, reported as one. The moment the build step corrects the design, the design HTML
   stops being a faithful preview and we're back to mangling.
4. **Three flags decide whether mobile works at all** — `multipleBreakpointsEnabled: true`,
   `hasLightbox: false`, and every `scale` numeric (never the string `"fit"`). All three
   present as "fine in the editor, broken on a real phone". Checked in step 4, every time.
   `references/format.md`.
5. **The stylesheet targets classes, never element ids.** `class="…"` in the design HTML
   ships as the element's `customClassnames` — the editor's own custom-class field. An
   id-per-element selector list is duplicated CSS the client can't reach, and it silently
   stops matching the moment an element is replaced. `references/format.md`.
6. **Never emit an unproven shape.** Video and lightboxes have no verified in-file form —
   the right answer is "add it natively in the editor", not a guess that looks right in
   the editor and breaks live. All six form field types ARE proven (2026-07-29 two-probe
   fit — `references/format.md` → Forms) and emitted.
7. **Never widen the transcriber to accommodate one design.** A genuinely new capability
   comes from the probe loop first: generate a small varied page, upload it, **download it
   again**, diff. What Unbounce changed is the answer. Then write the emitter, then write the
   fact into `references/format.md`.

## References

| File | When |
|---|---|
| `references/format.md` | before touching the transcriber, or when a page imports but renders wrong. Read all of it |
| `skills/design-page/references/grid.md` | for context when a geometry validator error isn't obvious |
| `skills/design-page/references/design-rules.md` | for context on what the design contract promised |

## Scripts

| Script | Deps |
|---|---|
| `scripts/transcribe.py design.html out.unbounce` | **Python stdlib only** — no pip, no network |
| `scripts/test_transcribe.py` | run after changing the transcriber |

For anything non-trivial, spawn the `unbounce-native:build-pack` agent (that exact agent
type — it is not named after this skill) — it holds the format spec so the calling
context doesn't have to.

```bash
python3 skills/build-page/scripts/test_transcribe.py
```
