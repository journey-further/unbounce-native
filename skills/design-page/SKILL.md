---
name: design-page
description: Build a natively-editable Unbounce landing page. Designs tight to the Unbounce Classic spec, then transcribes the design into a real .unbounce file of native lp-pom-* elements the client can edit, duplicate and re-lay-out in the drag-and-drop editor — never one raw-HTML blob. Use when asked to build, design, or generate an Unbounce landing page or a .unbounce file, to get a design into Unbounce, or to make an existing Unbounce page natively editable.
---

# Unbounce native page

## The one thing that matters

The client's team must be able to edit the page **in the drag-and-drop editor**: change
copy, duplicate a card, spin up a variant. That rules out the common shortcut of dumping a
responsive HTML page into a single Custom HTML element — it imports, it looks right, and it
is dead to the editor.

So: **author real native `lp-pom-*` elements.**

That is only affordable because of the second thing: **design tight to the Unbounce spec
from the first pixel**, so transcription is mechanical. Every element maps 1:1 to one
`lp-pom-*` at the same geometry. Nothing gets reflowed, snapped or estimated after the fact.

> Designing freely and then fighting the result into Unbounce's shape is the failure mode
> this skill exists to avoid. If you find yourself wanting the build step to *fix* the
> design, fix the design.

## Flow

**1 · Brand → tokens.** Spawn `brand-extract` with whatever brand input exists (a skillui
URL, a `DESIGN.md`, a screenshot, a PDF). It returns colours, fonts, radii, spacing.
Brand is always an **input** — never bundled in this plugin.

**2 · Read the spec, then design.** Read `references/grid.md` and
`references/design-rules.md` before writing any markup. Author the design HTML directly to
the geometry system: canvas 1280, padding 70, 24 columns, pitch 48, rows of 12. When porting
a non-Unbounce source, snap every `left`/`top` to the grid **as you author** — foreign
padding values guarantee an error storm at transcribe time. If the design has more than one
form, exactly one survives, and **which one is a conversion decision**: state your choice
and the alternative in the build report. This is the main event and it's conversational —
the user steers copy, hierarchy and layout here.

**3 · Measure.** `node scripts/measure.mjs design.html desktop` and again with `mobile`.
The loop: measure → write the true text heights and image `data-nat` values back →
re-measure until stable → only then transcribe. Declared heights must **equal** measured
content height — if you are typing a round number, you are estimating; the `slack` report
catches over-tall text the same way `overflow` catches over-short. Overflow means the
design is wrong — fix it, don't transcribe it.

Method, learned the hard way: build a **two-section smoke file** and run this loop on it
before authoring the rest of the page — the foundational bugs surface against 40 elements
instead of 170. Past ~40 elements, keep the height table in a scratch script that
regenerates the geometry (start that generator before the markup, not after);
hand-patching inline styles one at a time is where the overlap bugs come from.
`transcribe.py` writes nothing on error, so run it early and often as a free dry-run.
`scripts/geometry.py` does the mechanical half: `tables`/`snap` for legal positions when
porting foreign values, `heights design.html desktop.json mobile.json --write` to write
measured text heights back without hand-patching. A **full-page screenshot pass at both
breakpoints is not optional** — no validator can see sibling overlap.

**4 · Mobile.** Spawn `mobile-derive` on the desktop design. It returns the
`@media (max-width:600px)` block plus a short report of the *decisions* it made ("hid the
header phone number — the CTA covers it"). The user overrides named decisions, never
coordinates. Re-measure at mobile.

**5 · Transcribe.** `python3 scripts/transcribe.py design.html out.unbounce --page-name "…"`.
Stdlib only, single pass, no network. It validates and refuses to write on any hard error.
For anything non-trivial, spawn `build-pack` — it owns the format spec so your context
doesn't have to.

**6 · Report.** Tell the user what to do in the editor: upload via All Pages → "Upload an
Unbounce Page", reset traffic mode off "weighted", check a **real phone** (the editor is
tolerant of render-breakers a real device is not), and add anything deliberately left to the
editor. The report ends with a **"Not in the file"** section enumerating every target
feature deliberately not expressed — refused primitives, unsupported CSS, dropped
decoration, editor-only behaviours, placeholder furniture shipped as-is, and any documented
flow step done another way. If you decided not to build something, it goes in this list. A
silent omission is the failure mode this section exists to prevent.

**Never block on approval mid-flow.** Build, then show something the user can react to. A
gate is only worth its interruption if the user can decide better than you can — on
geometry and platform mechanics they can't, and the build is cheap and idempotent. The
carve-out is conversion decisions (which form survives, whether placeholders ship): still
don't block, but state the decision and the alternative in the report.

## Hard rules

1. **Native elements only.** One `lp-code` element is a decorative flourish or a third-party
   embed. A page-shaped `lp-code` element is a failure. **The test is per element, not a
   running total** — twenty 32px icon embeds are fine; one 900px-tall embed is the failure.
   Every icon in the design ships as `lp-code` or an image; substituting a text glyph, or
   dropping it, goes in the handover.
2. **Nine primitives:** `root` `block` `box` `text` `image` `button` `form` `lp-code`
   `lp-stylesheet`. Express everything else *with* those. **No video, no lightbox** — see
   `references/ui-capabilities.md` for why the lightbox is an active landmine.
3. **One form per page** (Classic hard limit). Every other CTA anchors to it.
4. **The transcriber never moves anything.** Off-grid or off-canvas geometry is an error in
   the design. The moment the build step starts correcting the design, the design stops
   being a faithful preview and you're back to mangling.
5. **Three flags decide whether mobile works at all** — `multipleBreakpointsEnabled: true`,
   `hasLightbox: false`, and every `scale` numeric (never the string `"fit"`). All three
   present as "fine in the editor, broken on a real phone". `references/format.md`.
6. **The stylesheet targets classes, never element ids.** Anything the page stylesheet
   styles carries a custom class — `class="…"` in the design HTML ships as the element's
   `customClassnames`, which is the editor's own custom-class field. One rule serves every
   element that needs it, and the client can add or remove the class from the UI. An
   id-per-element selector list is duplicated CSS the client can't reach, and it silently
   stops matching the moment an element is replaced. `references/format.md`.
7. **Brand is never bundled.** No brand tokens, client assets or brand skill in this repo.
8. **CRO is out of scope.** Message match, funnel strategy and heuristic scoring are not
   this skill's job. This skill does exactly one thing: produce Unbounce pages that don't
   need fixing.

## References — read on demand, not up front

| File | When |
|---|---|
| `references/design-rules.md` | **before writing any markup** — the design contract, the form chrome, mobile rules |
| `references/grid.md` | **before placing anything** — geometry system, snap semantics, what the validator enforces |
| `references/format.md` | before touching the transcriber, or when a page imports but renders wrong |
| `references/ui-capabilities.md` | when deciding whether a feature is safe to express |

## Scripts

| Script | Deps |
|---|---|
| `scripts/transcribe.py design.html out.unbounce` | **Python stdlib only** — no pip, no network |
| `scripts/measure.mjs design.html [desktop\|mobile] [shot.png]` | node + Chromium + network (Google Fonts must load) |
| `scripts/geometry.py tables\|snap\|heights` | **Python stdlib only** — legal snap tables, nearest-legal value, measured-height write-back (`--write`) |
| `scripts/test_transcribe.py` | run after changing the transcriber |

The dependency split is deliberate: measurement happens at design time where a browser is
already available, which keeps the transcriber air-gappable and CI-safe.

## When the format doesn't answer a question

Probe, don't guess. Generate a deliberately varied page, upload it, **download it again**,
and diff. What Unbounce silently changed is the answer. Every non-obvious fact in
`references/format.md` was found that way.
