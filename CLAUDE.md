# unbounce-native — repo notes

A Claude Code plugin that builds natively-editable Unbounce landing pages. See `README.md`
for what it is and `skills/unbounce-page/SKILL.md` for how it works.

## Working in here

- **This repo is client-shippable.** Nothing brand-specific, client-specific or CRO-related
  gets tracked. Brand is an input resolved by `agents/brand-extract.md`; CRO stays in
  Journey Further's internal tooling.
- `ridgeline/` is the **untracked** working directory from the project this came out of —
  the design source, the earlier generator, both real Unbounce exports, and the long-form
  format notes. It is gitignored on purpose: it's the evidence base, not the deliverable.
  Read it freely; never move anything from it into a tracked path.
- The reference docs under `skills/unbounce-page/references/` are the persistence layer. If
  you learn a platform fact, it goes there or it's lost — that's what makes a cold-start
  session possible.
- Run `python3 skills/unbounce-page/scripts/test_transcribe.py` after touching the
  transcriber.

## The two rules that shape every decision

1. **Native elements, never a raw-HTML blob.** The client's team must be able to edit in the
   drag-and-drop editor. A page-shaped `lp-code` element is the failure mode this repo exists
   to avoid.
2. **The transcriber never adjusts geometry.** Off-grid or off-canvas is an error in the
   design. The moment the build step starts correcting the design, the design HTML stops
   being a faithful preview and we're back to mangling.

## Unproven means refuse, not guess

Video, lightboxes, `<select>` and `<textarea>` have no verified in-file shape. Emitting a
guess produces a page that looks right in the editor and is broken live — the worst possible
failure mode, because it passes review. Before adding any capability, probe: generate a
varied page, upload it, **download it again**, diff. That's how every non-obvious fact in
`references/format.md` was found.

## Status

v1 skeleton complete (2026-07-25): plugin manifests, skill + four reference docs, transcriber
with validators + tests, measure script, three agents. **Not yet proven end-to-end** — v1 is
done when the reference page has been rebuilt from a cold start (fresh context, design brief
+ brand tokens only) and the resulting `.unbounce` imports, renders correctly on a real
phone, and the client can drag a whole card as one unit.
