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

Four skills, split where a working session naturally ends. Each one runs from its own
`SKILL.md` with no memory of the others — the files on disk are the handover.

| | |
|---|---|
| `skills/design-page/` | brand → layout → measure loop → mobile → sign-off. Produces a measured `design.html` |
| `skills/build-page/` | `design.html` → `out.unbounce`. Mechanical, stdlib-only, offline |
| `skills/upload-page/` | `.unbounce` → an unpublished page in the account, verified. **Needs the Unbounce MCP** |
| `skills/edit-page/` | update a live page in place. **Not yet available** — see the file for what to do instead |

| | |
|---|---|
| `skills/build-page/scripts/transcribe.py` | design HTML → `.unbounce`. **Python stdlib only** |
| `skills/design-page/scripts/measure.mjs` | real-browser text heights, image sizes, overflow flags |
| `skills/design-page/scripts/geometry.py` | legal snap tables, nearest-legal value, measured-height write-back |
| `agents/brand-extract.md` | brand input (URL / `DESIGN.md` / screenshot / PDF) → tokens |
| `agents/mobile-derive.md` | desktop layout → mobile overrides + a decision report |
| `agents/build-pack.md` | design HTML → verified `.unbounce` archive |
| `scripts/guard-native-page.py` | `PreToolUse` hook — stops the two MCP tools that flatten a native page |

Design and build need no credentials and no network beyond design-time measurement. Uploading
and editing need the Unbounce MCP; without it those skills' tools are simply absent and the
rest is unaffected.

## Connecting an Unbounce account (optional)

Designing and building need nothing. To also upload and edit, paste an Unbounce API key when
the plugin asks for one at install (Unbounce: **Settings → API keys**). It goes to your OS
keychain, never to this repo. Leave it blank and everything except the two connected skills
still works.

The plugin bundles the MCP server itself — `.mcp.json` points at
[`journey-further/unbounce-mcp`](https://github.com/journey-further/unbounce-mcp), a fork of
[cgilchrist/unbounce-mcp](https://github.com/cgilchrist/unbounce-mcp) that adds the
`get_variant_elements` / `set_variant_elements` pair a native page needs. It is pinned to a
tag, so upgrading is a deliberate edit rather than whatever `npx` happens to resolve.

Two things to know:

- **First use opens a browser window to log in to Unbounce.** The API key alone doesn't cover
  the editor endpoints, so the server keeps a session in `~/.unbounce-mcp/session.json`. It's
  a one-time interactive step and it cannot be automated away.
- **If you already added this MCP by hand** (`claude mcp add unbounce …`), remove it, or you
  get every tool twice under two names.

`.mcp.json` and `plugin.json` changes need `/reload-plugins` or a restart to take effect.

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
python3 skills/build-page/scripts/test_transcribe.py
```
