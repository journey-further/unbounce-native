---
name: design-page
description: Design an Unbounce landing page as a measured design HTML file, tight to the Unbounce Classic geometry spec, ready for mechanical transcription. Covers brand tokens, layout, the measure loop and the mobile breakpoint, and ends at user sign-off. Use when asked to design, lay out, redesign or restyle an Unbounce landing page, to keep editing an existing design.html, or as the first step of building one. Does not produce the .unbounce file — that is build-page.
---

# Design an Unbounce page

## The one thing that matters

The client's team must be able to edit the finished page **in the drag-and-drop editor**:
change copy, duplicate a card, spin up a variant. That rules out the common shortcut of
dumping a responsive HTML page into a single Custom HTML element — it imports, it looks
right, and it is dead to the editor.

So the page ships as real native `lp-pom-*` elements. That is only affordable because of
what happens here: **design tight to the Unbounce spec from the first pixel**, so
transcription is mechanical. Every element in your design HTML maps 1:1 to one `lp-pom-*` at
the same geometry. Nothing gets reflowed, snapped or estimated after the fact.

> Designing freely and then fighting the result into Unbounce's shape is the failure mode
> this skill exists to avoid. If you find yourself wanting the build step to *fix* the
> design, fix the design.

## What you produce

One working folder containing:

| | |
|---|---|
| `design.html` | the design, with **measured** heights written back and a stable re-measure, plus the `@media (max-width:600px)` block |
| a design report | decisions made, conversion choices and their alternatives, anything deliberately left to the editor |

That folder is the handover. `build-page` turns it into `out.unbounce` and needs nothing
else — no memory of this conversation. **You never transcribe.**

## Resuming an existing design

"Pick up `design.html` and keep editing" is a first-class entry, not a special case. When
you start from an existing design file:

1. Read `references/grid.md` and `references/design-rules.md` first — the file's geometry
   only makes sense against them.
2. Re-measure before you change anything (step 3 below). A design file you did not measure
   is a design file whose heights you cannot trust.
3. Edit, re-measure, re-check the mobile block covers every positioned element, sign off.

Nothing here depends on how the file was created or which session created it.

## Flow

**1 · Brand → tokens.** Spawn the `unbounce-native:brand-extract` agent (that exact agent
type) with whatever brand input exists (a design
system doc, a URL, a screenshot, a PDF). It returns colours, fonts, radii, spacing. Brand is
always an **input** — never bundled in this plugin.

**2 · Read the spec, then design.** Read `references/grid.md` and
`references/design-rules.md` before writing any markup. Author the design HTML directly to
the geometry system: canvas 1280, padding 70, 24 columns, pitch 48, rows of 12. When porting
a non-Unbounce source, snap every `left`/`top` to the grid **as you author** — foreign
padding values guarantee an error storm at transcribe time. If the design has more than one
form, exactly one survives, and **which one is a conversion decision**: state your choice and
the alternative in the report. This is the main event and it's conversational — the user
steers copy, hierarchy and layout here.

**3 · Measure.** `node scripts/measure.mjs design.html desktop` and again with `mobile`.
The loop: measure → write the true text heights and image `data-nat` values back →
re-measure until stable → only then sign off. Declared heights must **equal** measured
content height — if you are typing a round number, you are estimating; the `slack` report
catches over-tall text the same way `overflow` catches over-short. Overflow means the design
is wrong — fix it, don't hand it on.

Method, learned the hard way: build a **two-section smoke file** and run this loop on it
before authoring the rest of the page — the foundational bugs surface against 40 elements
instead of 170. Past ~40 elements, keep the height table in a scratch script that regenerates
the geometry (start that generator before the markup, not after); hand-patching inline styles
one at a time is where the overlap bugs come from. `scripts/geometry.py` does the mechanical
half: `tables`/`snap` for legal positions when porting foreign values, `heights design.html
desktop.json mobile.json --write` to write measured text heights back without hand-patching.
A **full-page screenshot pass at both breakpoints is not optional** — no validator can see
sibling overlap.

`build-page`'s transcriber writes nothing on error, so it doubles as a free dry-run
validator: `python3 skills/build-page/scripts/transcribe.py design.html /tmp/probe.unbounce`.
Run it early and often, delete the output. Getting it to exit 0 is not sign-off — it cannot
see whether the design is any good.

**4 · Mobile.** Spawn the `unbounce-native:mobile-derive` agent (that exact agent type) on
the desktop design. It returns the
`@media (max-width:600px)` block plus a short report of the *decisions* it made ("hid the
header phone number — the CTA covers it"). The user overrides named decisions, never
coordinates. Re-measure at mobile.

**5 · Sign-off.** Show the user the screenshots and the design report: what you built, the
conversion decisions and their alternatives, and what is deliberately left for the editor.
This is where the skill ends. Building the file is `build-page`; it can run now, in an hour,
or in a different session.

**Never block on approval mid-flow.** Build, then show something the user can react to. A
gate is only worth its interruption if the user can decide better than you can — on geometry
and platform mechanics they can't, and the design loop is cheap and idempotent. The carve-out
is conversion decisions (which form survives, whether placeholders ship): still don't block,
but state the decision and the alternative in the report.

## Hard rules

1. **1:1 isomorphism.** One element in the design HTML = one `lp-pom-*` element at the same
   geometry. If a piece of the design cannot be expressed that way, change the design — do
   not expect the build step to interpret it.
2. **Nine primitives:** `root` `block` `box` `text` `image` `button` `form` `lp-code`
   `lp-stylesheet`. Express everything else *with* those. **No video, no lightbox** — see
   `references/ui-capabilities.md` for why the lightbox is an active landmine.
3. **Native elements only.** One `lp-code` element is a decorative flourish or a third-party
   embed. A page-shaped `lp-code` element is a failure. **The test is per element, not a
   running total** — twenty 32px icon embeds are fine; one 900px-tall embed is the failure.
   Every icon in the design ships as `lp-code` or an image; substituting a text glyph, or
   dropping it, goes in the report.
4. **One form per page** (Classic hard limit). Every other CTA anchors to it.
5. **Off-grid or off-canvas geometry is an error in the design**, and the build step will
   refuse it rather than correct it. That refusal is the feature: the moment anything
   downstream starts adjusting geometry, this file stops being a faithful preview and you're
   back to mangling.
6. **Style with classes, not per-element ids.** Anything the page stylesheet styles carries a
   `class="…"` in the design HTML — it becomes the element's custom-class field in the editor,
   so one rule serves every element that needs it and the client can add or remove it from
   the UI. Ids in the stylesheet are CSS the client can't reach.
7. **Nesting is the alignment tool.** Boxes nest to any depth, and children are
   parent-relative. A card is a box with its contents inside it — that is what lets the
   client drag the whole card as one unit. A flat page of absolutely-positioned siblings
   passes every validator and fails the client.
8. **Brand is never bundled.** No brand tokens, client assets or brand skill in this repo.
9. **CRO is out of scope.** Message match, funnel strategy and heuristic scoring are not this
   skill's job.

## References — read on demand, not up front

| File | When |
|---|---|
| `references/design-rules.md` | **before writing any markup** — the design contract, the form chrome, mobile rules |
| `references/grid.md` | **before placing anything** — geometry system, snap semantics, what the validator enforces |
| `references/ui-capabilities.md` | when deciding whether a feature is safe to express |
| `skills/build-page/references/format.md` | rarely, and for context only: what the design HTML becomes in the file |

## Scripts

| Script | Deps |
|---|---|
| `scripts/measure.mjs design.html [desktop\|mobile] [shot.png]` | node + Chromium + network (Google Fonts must load) |
| `scripts/geometry.py tables\|snap\|heights` | **Python stdlib only** — legal snap tables, nearest-legal value, measured-height write-back (`--write`) |

Measurement happens here, at design time, where a browser is already available. That is what
keeps `build-page` air-gappable and CI-safe.

## When the spec doesn't answer a question

Probe, don't guess. Generate a deliberately varied page, upload it, **download it again**,
and diff. What Unbounce silently changed is the answer. Every non-obvious platform fact in
these references was found that way, and a new one gets written into a reference doc the same
day it's found — the references are the persistence layer.
