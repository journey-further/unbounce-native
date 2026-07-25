# Geometry system, grid and snap semantics

The numbers here are not conventions — they are the whole reason a design can be
transcribed mechanically. Design to them from the first pixel.

## The canvas

| | Canvas | Padding | Cols | colW | Pitch | Content | rowHeight | yGap |
|---|---|---|---|---|---|---|---|---|
| **Desktop** | 1280 | 70 | 24 | **36** | **48** | 1140 | 12 | 0 |
| **Mobile** | 320 *(hard cap)* | 10 | 6 | **40** | **52** | 300 | 12 | 0 |

Every derived quantity is an integer, and on desktop `colW`, `pitch`, `xGap` and `content`
are all multiples of 12 — spans, gutters and the row grid are one coherent system. (1280
and 70 are not multiples of 12 themselves; they are chosen *because* they make the derived
numbers come out clean.)

- **Column line k** = `padding + k · pitch` — always an integer.
- **Whole spans:** desktop `48n − 12` → 36, 84, 132, 180, 228, 276 … 1140.
  Mobile `52n − 12` → 40, 92, 144, 196, 248, **300** (= full width).
- Column tiling: 4 cards = 6+6+6+6 cols, 3 = 8+8+8, 2 = 12+12, gutter = xGap 12.

**Why 1280 and not 1440.** Effective scale for a narrow viewport is
`min(1, viewport ÷ canvas)`. A 1440 canvas serves a 1024px viewport (iPad landscape, small
laptops, half-screen windows) at **71%**; 1280 serves it at **80%** and renders 1:1 at the
very common 1280 viewport. Content width is 1140 either way — the choice only moves where
the padding sits. Blocks are `fitWidthToPage: true`, so backgrounds stay full-bleed on
large monitors regardless.

**Why padding 70.** At canvas 1280 / 24 cols / `xGap 12`, padding 70 is the only value that
makes `colW` a *multiple of 12* (36). Any padding ≡ 10 (mod 12) yields an integer `colW`;
the 12-multiple is what we select for.

**Why mobile padding 10 and not 16.** Below the breakpoint crossover the 320 column is
**centred**, so a 400px phone already has ~40px of natural margin before section padding.
Edge safety is satisfied, and 300px of content is *more* than Unbounce's own 296 default.

**Why `rowHeight 12 / yGap 0`.** Snap points sit at row **top and bottom**, so `rh12/yGap12`
and `rh12/yGap0` are identical (verified in-editor) and `yGap 0` renders less chaotically.
`rh 8` felt like too much snapping. 12px keeps the worst-case snap nudge to 6px.
The stock `rh24/yGap12` interleaves unevenly (points at 0, 24, 36, 60, 72…), which is why
the default grid feels awkward to work against.

⚠️ **The grid cannot force spacing** — it only offers positions. Consistent vertical rhythm
comes from design spacing tokens, not from the grid.

⚠️ **The 600px crossover is approximate and the contract hardcodes it.** "~600px" comes from
documentation, not a pixel-level probe. Two consequences: the `@media (max-width:600px)`
boundary may be a few pixels off Unbounce's real switchover, and between **321–599px
Unbounce centres the 320 column** while the design HTML anchors it left. Cosmetic, narrow
window — worth pinning with a probe when convenient.

## The grid is author-controlled, not a platform constant

`columns` is settable **1–50** per section, padding **0–200px** per side, and
`columns`/`rowHeight`/`xGap`/`yGap` are **separately configurable for desktop and mobile**.
`showGrid` is page-level (on `lp-pom-root`); `snapToGrid` is per-section (on each
`lp-pom-block`). Real exports differ wildly — one blank page ships desktop
`24/rh24/gaps12/pad80,56`, a template-derived page ships `50/rh8/gaps0/pad88,72`. Those are
defaults, not limits. We write the table above onto every section instead.

## Snap semantics (verified in an editor session)

- **Snap affects SIZE as well as position.** Resizing snaps the dragged edge to the grid.
  But it only bites **when a user actually resizes** — off-grid sizes are perfectly legal in
  the file and render exactly as authored.
- **There is no centre anchor.** Each *edge* snaps independently on each axis. What looks
  like centre-snapping is element-to-element alignment.
- **Element-to-element alignment snapping survives `snapToGrid: false`.** Turning the grid
  off gives free move *and* free resize, and the client still gets alignment guides. So
  disabling grid snap does not cost the client alignment help.
- **The grid never affects the visitor.** An element parked 7px off-grid renders 7px off in
  preview and live, regardless of grid config. It is editor chrome.
- Sections carry a **height** (width is not settable) and a **"gap below"**
  (`geometry.margin.bottom`), plus per-section padding.
- **Mobile is hard-capped at 320px.** Setting `root.breakpoints.mobile.geometry.contentWidth:
  375` is **ignored** — content beyond 320 renders but anchors left and the editor throws
  "out of bounds" warnings. This is the one dimension where the file cannot exceed the UI.

## What the validator enforces, and why it is graded

Snapping is latent damage: an off-grid element is never *wrong* in the file, it only jumps
if and when the client clicks it. So conformance is graded by consequence.

| | Check | Level |
|---|---|---|
| **`left` / `top`** | on a column/row snap point at **both** breakpoints | **error** — this is what prevents click-jump |
| **`width`** | a whole span (`pitch·n − 12`) | **warning** — legal, sometimes deliberate, usually a design smell at 24 columns |
| **`height`** | — | **no check** — measured content height must win |
| **right edge** | `left + width ≤ canvas` at both breakpoints | **error** — catches double-counted nesting offsets and the mobile 320 cap |

Snap points are `{pad + k·pitch} ∪ {pad + k·pitch + colW}` horizontally (each edge snaps
independently, so a column's right edge is a legal left position) and multiples of
`rowHeight` vertically.

**Heights are deliberately free.** Forcing them onto 12px multiples would re-introduce the
height-estimation error that measurement exists to remove. A client resize nudges a height
by ≤6px, the text reflows slightly, and that is acceptable and rare.

### Grid conformance applies to a block's DIRECT children only

A box and the content inside it cannot *both* sit on the grid unless the padding happens to
be a whole grid unit — snapping each independently collapses the padding. So the **card
rides the grid and its contents keep their padding**: nested offsets are the designer's
padding, not grid positions, and the validator exempts them. Full-bleed elements
(width ≥ 98% of canvas) are exempt too — they intentionally overscan.

Where the padding *can* be a whole span multiple, prefer it. Nothing forces it.

**The design owns the snapping; the validator only checks the result.** The transcriber must
never adjust geometry — the moment it does, it is a mangler again and the design HTML stops
being a faithful preview.
