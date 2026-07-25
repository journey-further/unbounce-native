# unbounce-native — backlog

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

## Validate the design form HTML against Unbounce's real form chrome
**Origin:** decision 16 — the form is a real `<form>` in the design HTML, so its height is
measured rather than estimated.
**Idea:** the design-time CSS in `references/design-rules.md` approximates Unbounce's field
chrome (71px stride, 53/34/15 container/input/label). Real Unbounce wraps fields in its own
markup with its own padding, label placement and submit metrics, so measured form height is
**close, not exact** — and because everything below the form stacks from that height, the
error propagates down the page. Extract the real published field markup and mirror it.
**Context for next agent:**
- Cheapest route: publish a page with a form, view source, lift the rendered field markup and
  computed styles. Then measurement is exact rather than approximate.
- `publishedStyles` shapes are already confirmed (top-level array, 3 entries per field, 71px
  stride, independent copies per breakpoint). The open question is only the *rendered* chrome.
- Only worth doing once the rest of the pipeline is measuring accurately — a refinement on a
  working loop, not a blocker.

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

## Confirm `company_id: 0` is accepted on asset ingestion
**Origin:** the transcriber generates the archive from scratch rather than cloning an account
export, so it has no real `company_id` to reuse.
**Idea:** asset records carry `company_id`, and the only value ever verified is a real
account's. `0` is the default and is probably ignored on import (the server re-ingests the
file), but it is untested.
**Context for next agent:**
- Test on the next upload: if images come through, `0` is fine and this closes.
- If ingestion fails, `--company-id N` already exists — lift the real value from any export of
  the target account, and document that in `references/format.md`.
- Related unknown, same test: whether the from-scratch archive tree (rather than a cloned
  known-good skeleton) imports cleanly. The previous approach cloned an export; this one
  builds the tree from documented shapes. `unbounce-mcp` proves minimal sidecars are accepted,
  so the risk is low, but it is the one structural thing this rewrite hasn't proven.
