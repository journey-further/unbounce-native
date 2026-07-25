# unbounce-native

A Claude Code plugin for building **natively-editable** Unbounce landing pages.

The usual way to get a design into Unbounce is to paste it into one Custom HTML element. It
imports, it looks right, and it's dead to the drag-and-drop editor — nobody on the client's
team can change a headline, duplicate a card or spin up a variant.

This plugin authors **real native `lp-pom-*` elements** instead. The client edits the page
exactly as if they'd built it by hand.

That's affordable because of one inversion: the design is authored **tight to the Unbounce
Classic spec from the first pixel** — its canvas, its column grid, its 320px mobile cap — so
turning the design into a `.unbounce` file is mechanical transcription rather than a
post-hoc mangling pass. There is no reflow step, no height estimation, no rebuild loop.

## Install

```
/plugin marketplace add journey-further/unbounce-native
/plugin install unbounce-native
```

Then just ask for what you want: *"build me an Unbounce landing page for …"*.

## What's in it

| | |
|---|---|
| `skills/design-page/` | the skill: how to design for the platform, plus the reference docs |
| `skills/design-page/scripts/transcribe.py` | design HTML → `.unbounce`. **Python stdlib only** |
| `skills/design-page/scripts/measure.mjs` | real-browser text heights, image sizes, overflow flags |
| `agents/brand-extract.md` | brand input (URL / `DESIGN.md` / screenshot / PDF) → tokens |
| `agents/mobile-derive.md` | desktop layout → mobile overrides + a decision report |
| `agents/build-pack.md` | design HTML → verified `.unbounce` archive |

## Requirements

- **Transcription:** Python 3, stdlib only. No pip, no network — works offline and in CI.
- **Measurement:** `npm install` (Playwright + Chromium) and network access, because Google
  Fonts must actually load for text metrics to be real.
- **Unbounce:** a **Classic Builder** account. Smart Builder pages cannot be exported or
  imported at all.

## Brand is an input, never bundled

No brand tokens, client assets or brand skill are tracked in this repo — by construction, so
no client's brand can ever ship inside it. Brand arrives per-project via `brand-extract`
from a design-system doc, a URL, a screenshot or a PDF.

## What it deliberately doesn't do

- **No CRO.** Message match, funnel design, heuristic scoring and copy strategy are somebody
  else's job. This plugin does exactly one thing: produce Unbounce pages that don't need
  fixing.
- **No video or lightbox elements.** Neither has a verified in-file shape, and a lightbox
  flag set wrong silently collapses the live mobile layout to desktop. A video becomes an
  embed; a lightbox CTA becomes an anchor.
- **No `<select>` / `<textarea>` form fields.** Same reason — add them natively in the editor
  after import, which takes about ten seconds.

Guessing at an unproven shape produces a page that looks fine in the editor and is broken on
a real phone. The plugin refuses instead.

## Tests

```bash
python3 skills/design-page/scripts/test_transcribe.py
```
