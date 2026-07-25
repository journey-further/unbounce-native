# unbounce-native — backlog

## Probe: native gradient backgrounds (`newBackground.type: "gradient"`)
**Origin:** bakeoff finding F16 — all three cold-start arms named the hero's
`linear-gradient` overlay as the largest visible fidelity loss; `format.md` used to promise
gradients the emitters can't write (every emitter is `solidColor`-only; doc corrected).
**Idea:** lift the real gradient JSON shape from a template export if one carries it, emit it
on a block and a box in a probe page, upload, **download again**, diff. If it round-trips,
add gradient support to `transcribe.py` — the single highest-fidelity capability available.
**Context for next agent:** the probe-then-diff pattern is in `format.md`; the root element
already carries a vestigial `gradient.baseColor` key to compare against. Unproven means
refuse — do not emit a guessed shape.

## Parse real box-shadow values into `_effect()`
**Origin:** bakeoff finding F20 — `box-shadow` is read as a boolean and every shadow ships
at fixed opacity 22 / offset 12 / blur 34; arm c lost two visibly different shadows to it.
**Idea:** parse the shorthand's offset/blur/rgba into the effect JSON. Mechanical, no probe
needed — the shape already ships with constants, this only fills it with the design's values.
**Context for next agent:** `_effect()` in `transcribe.py`; `hexcolor()` now finds colour
tokens anywhere in a shorthand. Add a `test_transcribe.py` case. Docs currently state the
boolean behaviour (`design-rules.md` box bullet) — update them when this lands.

## Re-factor `mobile-derive` to return decisions + a height table, not a CSS block
**Origin:** bakeoff finding F22 (supplement) — arm c argued a standalone `@media` block
competes with generator-owned geometry: "mobile-derive should return decisions plus a height
table, so its output composes with a generator instead of competing with one."
**Idea:** change the agent's contract so the parent (or its scratch generator, per SKILL.md
step 3) derives the geometry from the agent's editorial decisions and measured heights.
**Context for next agent:** the interim fix (a transcribe.py exit gate in
`agents/mobile-derive.md`) already stops non-conformant output; this entry is the deeper fix.
Decide against the evidence in `ridgeline/BAKEOFF-FINDINGS.md` F22 — the editorial half of
the agent is proven valuable, the geometry half caused every defect.

## Probe: the `<p>` strut floor in `measure.mjs`
**Origin:** bakeoff finding F5b — a `<p>` at `line-height:normal` floors `contentHeight()`
at ~22px, so small captions "measure" 22 and ~30 elements per page carry harness-inflated
heights. Open question: does the same strut exist in Unbounce's live render (making the
measurement *correct*), or is it preview-only slack?
**Context for next agent:** decide between requiring `line-height` on the `<p>` in the
design contract vs neutralising the strut in `contentHeight()` — **probe first** (upload a
page with a 10px caption, measure the live element). Cautionary: arm b's blanket
`line-height:0` collapsed multi-line wraps — the design-contract route needs a real value,
not a zero.

## Prove v1 end-to-end from a cold start
**Origin:** the plan's definition of done. The skeleton is built but nothing has been
generated through it yet.
**Idea:** in a **fresh context**, rebuild the reference page importing only the design brief
plus brand tokens — no memory of how it was built the first time. Then upload it and check a
real phone.
**Context for next agent:**
- This is a **test of the packaging as much as the pipeline**. Anything not written into
  `skills/design-page/references/` is lost when that session begins. If the cold session
  has to ask a question the references should have answered, that's the finding — fix the
  reference doc, don't answer it inline.
- **Run it on three tiers: Sonnet/medium, Sonnet/high, Opus/high.** Same brief, same brand
  tokens, three fresh sessions. The instructions are the variable under test, not the model —
  anything Opus gets right and Sonnet/medium doesn't is a gap in `SKILL.md` or a reference
  doc, so fix the doc rather than raising the floor. Watch specifically for: skipping the
  measure step, guessing an unproven primitive instead of refusing, and "correcting" a design
  in the transcriber instead of in the design HTML.
- Consequence for the agents: **leave `model:` out of the agent frontmatter** so all three
  runs vary end-to-end. Pin a tier only if a run shows a specific agent needs one.
- Definition of done: imports; renders correctly **live** on mobile (not just editor
  preview); images correct; the client can drag a whole card as one unit.
- Benchmark from the previous, mangler-based approach: 87/104 mobile elements landed within
  20px of a hand-placed export. Beat that without a post-hoc pass.
- The old working material — design source, the earlier generator, both real exports — is in
  the untracked `ridgeline/` directory. Use it as evidence, don't copy from it.

## Pin the mobile breakpoint crossover empirically
**Origin:** `references/grid.md` hardcodes `@media (max-width:600px)`.
**Idea:** "~600px" comes from documentation, not a probe, and the confirming article is one
that 403s automated fetchers. Two consequences worth measuring: the exact switchover pixel,
and the 321–599px band where Unbounce **centres** the 320 column while the design HTML
anchors it left.
**Context for next agent:**
- Cheap probe: publish a page with a visually distinct marker at each breakpoint, then resize
  a real browser through 560–640px and watch where it flips.
- If the boundary is meaningfully off 600, the media query in the design contract moves and
  `mobile-derive` needs telling.
- The centring mismatch only affects preview faithfulness in that narrow band, not the built
  page. Fix it with a centred 320 wrapper in the design-time CSS if it starts to mislead.

## How prescriptive should size-snapping be?
**Origin:** decision 11 — conformance is graded by consequence: positions error, widths warn,
heights unchecked. That split is a reasoned guess, not a measured one.
**Idea:** work out the right level of prescription once real pages exist. How often does a
client resize at all? Which elements? Does an off-grid width ever cause a *visible* problem
before someone touches it?
**Context for next agent:**
- Platform fact: snapping applies to the dragged edge on resize as well as to position on
  move, and each edge snaps independently (no centre anchor). Off-grid sizes are legal and
  render exactly as authored — the jump is latent, triggered only by a client resize.
- Why heights are exempt: measured text heights are the whole point. Forcing them onto 12px
  multiples re-introduces the estimation error that caused six rounds of mobile QA on the
  previous approach. A ≤6px nudge on resize is acceptable and rare.
- Why widths only warn: whole spans are the discipline we *want* for tiling rows, but
  full-bleed images, centred decorations and text blocks legitimately sit off-span. An error
  would block valid designs.
- Decision tree: if clients turn out to resize cards often → promote widths to an error. If
  nobody resizes → relax widths to advisory and stop spending validator complexity. If
  heights jump visibly → revisit whether *card* heights (authored, unlike text heights)
  should be row multiples.
- Cheap probe: set a height deliberately off-grid, resize it in the editor, measure the
  actual displacement to confirm the ≤6px assumption at `rowHeight 12`.

## Add video + lightbox primitives when a real brief needs one
**Origin:** decision 9 — the palette is restricted to the nine primitives a real 92-element
page actually used.
**Idea:** add `lp-pom-video` and lightbox buttons/sub-pages only when a brief genuinely
requires one, with a probe page proving the shape round-trips first.
**Context for next agent:**
- Video appears in the blank-template sampler but in **no** real export — an untested path.
- The lightbox is an active landmine, not merely untested: `hasLightbox: true` with no
  lightbox sub-page makes the **live** renderer hunt for missing data and collapse the whole
  page to the desktop layout on mobile. The editor is tolerant, so it presents as "works in
  preview, broken live until I open and save". Supporting lightboxes means generating
  sub-page trees *and* getting that flag right.
- Interim workarounds that stay client-editable: a video section becomes an `lp-code` embed; a
  lightbox CTA becomes a second page or an anchor.

## MCP auto-upload
**Origin:** `github.com/cgilchrist/unbounce-mcp` — attractive for auto-upload and for reading
an existing page back.
**Idea:** slot it in so the pipeline can upload without the web UI, and so probe-then-diff
becomes a single command instead of a manual download.
**Context for next agent:**
- **Blocked:** generating an Unbounce API key needs an account access level we don't have yet.
- Note the tool's own approach is the anti-pattern this plugin exists to avoid — it stuffs the
  whole page into one `lp-code` element and hand-wires forms via a script. Use it for
  transport only, never for generation.
- There is no public import API; the tool drives the same web upload path.
