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
**Status (2026-07-28):** scheduled as PLAN-v2 Phase 3 — run by us before handover; context below still applies.
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

## Expose the native element array in unbounce-mcp (upstream PR)
**Status (2026-07-28):** absorbed into PLAN-v2 D2/Phase 2 — pair lands in a JF fork now, PR upstream in parallel (ADR 0001).
**Origin:** MCP integration session 2026-07-28. Three separate backlog items below are all
blocked on the same missing pair of tools, which makes this the keystone.
**Idea:** add `get_variant_elements` / `set_variant_elements` to
`github.com/cgilchrist/unbounce-mcp` — read and write a variant's raw `elements` array,
unfiltered. Both halves of the machinery already exist internally: `fetchVariantState`
(`src/direct.js:452`) parses the array out of `edit.json`, and `directEditVariant`
(`src/direct.js:559`) writes a whole array back via `edit.json` + `save.xml`. Neither is
reachable as a tool.
**Context for next agent:**
- Why it's needed: `get_variant` classifies our native pages as `classic_builder`
  (`src/direct.js:499-515` — we have `lp-pom-text` siblings and no `lp-code-1` body), so it
  returns a rendered preview plus modernization hints instead of the element array.
- Prefer an upstream PR to a fork: the pair is generically useful and the repo is public.
  Keep our two banned tools banned regardless (see below).
- Once landed, three things become possible in one or two calls each: probe-then-diff, native
  A/B variants on live pages, and in-place edits.

## Never call `deploy_page` or `edit_variant` on a native page
**Status (2026-07-28):** confirmed — lands with the `upload-page`/`edit-page` skill docs (PLAN-v2 Phases 1–2).
**Origin:** MCP integration session 2026-07-28 — read of the MCP source.
**Idea:** if MCP calls become part of the documented flow, this belongs in `SKILL.md` as a
hard rule, not as tribal knowledge.
**Context for next agent:**
- `deploy_page` — its packager builds one `lp-code` element at 1440×10000 with the whole body
  inside (`src/packager.js:301`). Precisely the failure mode this repo exists to avoid.
- `edit_variant` — overwrites the content of the **first `lp-code` element it finds**
  (`src/direct.js:550`). On our pages that is an *icon embed* (`transcribe.py:395`), so it
  would silently replace a 32px icon with an entire page. It will look like it worked.
- Safe by contrast: `duplicate_variant` is a server-side GraphQL mutation
  (`src/direct.js:339`) — Unbounce copies elements natively with no HTML round-trip.

## Probe-then-diff as one command
**Status (2026-07-28):** absorbed into PLAN-v2 — P3/P4 plus the definition-of-done line "the round-trip probe runs as a command".
**Origin:** MCP integration session 2026-07-28. `SKILL.md`'s closing rule ("upload it,
download it again, and diff") is a manual browser loop, which is why it has only ever run
during the bakeoff.
**Idea:** given the element read above, make verification a script: transcribe → upload →
read elements back → diff against what we emitted. Every non-obvious fact in `format.md` was
found this way; the loop being manual is what caps how often we learn one.
**Context for next agent:**
- **Not coupled to the upload step.** Verification works on published pages too
  (`screenshot_variant` takes `source: "published"`, and the element read is state-agnostic),
  so this is worth doing even if we never adopt MCP upload.
- `screenshot_variant` already gives useful render verification today with no MCP change —
  it returns desktop plus tiled mobile in one call. Proven 2026-07-28.
- What a diff must tolerate: Unbounce rewrites ids, asset UUIDs and timestamps on import.
  Diff the *shapes and geometry*, not the bytes.

## Pull an existing page, change it, push it back in place
**Status (2026-07-28):** promoted — this is now a fundamental v2 flow, the `edit-page` skill (PLAN-v2 Phase 2). Asset wrinkle below still applies.
**Origin:** Sam, 2026-07-28 — "pulling landing pages, making changes, and pushing them back
again — is that possible or would the upload force it into a new landing page?"
**Idea:** a round-trip that preserves the page's identity. Answer to the question: a
`.unbounce` **file** upload can never update in place — it goes through the UI's importer
(`page_uploads/import_upload.json`, `src/upload.js:52`), which always creates a new page and
takes no page id. The in-place path is the element array instead: read it, patch it locally,
write it back. Page id, URL, stats, leads, form integrations and published state all survive.
**Context for next agent:**
- Blocked on the keystone entry above.
- **The asset wrinkle:** our `.unbounce` carries images as `assets/<uuid>/` inside the tarball
  (`transcribe.py:607`), and pushing only an element array creates no assets. Any *new* image
  must go through `upload_image` first and the element rewritten to the returned CDN URL.
  Unchanged images are fine. This is the one place `upload_image` earns a place in our flow.
- Why it matters more than re-uploading: you cannot re-upload a page that already has traffic
  without abandoning its stats, leads and integrations.

## Skill: clone a live page into an A/B variant
**Status (2026-07-28):** scheduled as PLAN-v2 Phase 4, bolted onto `edit-page`; not handover-blocking.
**Origin:** Sam, 2026-07-28 — "a skill that potentially pulls an existing page and creates a
variant of it for A/B testing".
**Idea:** `duplicate_variant` (native, safe) → patch the copy's elements → `rename_variant` →
`set_variant_weights` → later `get_page_stats` → `promote_variant`. Natively editable
throughout, so the client can still work on either variant in the editor.
**Context for next agent:**
- Blocked on the keystone entry for the patch step. Everything either side of it works today.
- **Lazy alternative with a real ceiling:** teach `transcribe.py` to emit multiple variants in
  one `.unbounce` (the format supports `a`–`z`; we hardcode one) and upload with
  `variant_weights`. No MCP change, entirely in our own repo — but it only works for *new*
  pages, so it does not replace the in-place route.
- Keep the *choice* of what to test out of scope — that's CRO, hard rule 8.

## Instrument existing pages — script slots + DTR
**Status (2026-07-28):** judgement call resolved by PLAN-v2 D5 — not a shippable product of this repo; per-client enhancement or internal tooling.
**Origin:** MCP integration session 2026-07-28.
**Idea:** `set_javascripts` writes the Head / After Body / Before Body End slots (GTM, GA,
Meta pixels); `set_dynamic_text` sets up DTR against a URL query param for paid campaigns.
**Context for next agent:** probably the fastest standalone win on this list — zero design
work, needs none of the keystone work, and applies to **any** page in a client's account
including ones we did not build. Decide whether it belongs in this repo at all or in Journey
Further's internal tooling; it is page plumbing rather than page construction, so it is a
genuine judgement call.

## Rebuild a client's Classic Builder pages natively
**Origin:** MCP integration session 2026-07-28 — the MCP advertises "modernization" and does
it by producing an `lp-code` blob.
**Idea:** point the existing skill at a legacy page instead of a design brief: read the page,
derive the design HTML, run the normal measure → transcribe flow, ship native elements. A
strictly better version of something the MCP already offers.
**Context for next agent:** `get_variant` on a Classic Builder variant returns pre-extracted
`font_inventory`, `image_inventory`, `layout_hints` and `design_width` — genuinely useful as
*input* even though its intended output is the blob we refuse to ship. Ignore
`get_classic_builder_modernization_guidelines`; it optimises for the wrong target.

## Brand intake from an existing Unbounce page
**Origin:** MCP integration session 2026-07-28.
**Idea:** add "an existing Unbounce page" to the input types `agents/brand-extract.md`
accepts, alongside the skillui URL / `DESIGN.md` / screenshot / PDF it takes now.
`screenshot_variant` plus `get_variant` gives fonts, colours and logo CDN URLs as ground
truth rather than inference.
**Context for next agent:** brand stays an **input** — hard rule 7. This adds a source, it
does not bundle anything.

## Get a sandbox Unbounce sub-account
**Status (2026-07-28):** superseded by PLAN-v2 D7 — no sandbox while nothing is live (throwaway pages, `publish: false`); revisit the moment a domain is genuinely connected.
**Origin:** MCP integration session 2026-07-28 — the account has exactly one sub-account,
a live client one.
**Idea:** a sandbox client with its own API key before we automate any write path.
**Context for next agent:**
- Every MCP write currently lands in a live client account. Test pages must be prefixed and
  deleted by hand, which is exactly the discipline that fails under time pressure.
- The MCP's own test harness expects this: `.env.test` wants
  `UNBOUNCE_SANDBOX_SUB_ACCOUNT_ID` and a separate session file specifically so the harness
  cannot reach production clients.
- This is a prerequisite for the A/B and in-place entries, not a nice-to-have.

## Deprioritised: MCP upload as a flow step
**Status (2026-07-28):** revived as the `upload-page` skill (PLAN-v2, connected-only). The operational gotchas below feed straight into that skill.
**Origin:** proven working 2026-07-28 (`upload_unbounce_file` → preview → screenshot), then
judged not worth it by Sam: "Ship is good, but also potentially not worth the API key
requirement."
**Idea:** kept as a note, not a task. The manual upload is ~30 seconds and needs no
credentials; the MCP path needs an API key *and* a Playwright browser session. Reach for it
when a flow already needs the MCP for another reason — verification, variants — rather than
for upload alone.
**Context for next agent:** if it is revived, `publish` defaults to **true** — pass
`publish: false`. The page name inside the `.unbounce` overrides the `page_name` argument.
`set_traffic_mode` returned `Unauthorized` in `pending_steps` on a single-variant upload and
was safely ignorable (one variant at weight 100); re-run the pending step rather than
re-deploying. First run also needs the chromium build the MCP's own Playwright expects —
1234 for Playwright 1.62.0 — installed via its CLI in `~/.npm/_npx/<hash>`, not via a bare
`npx playwright install chromium`.
