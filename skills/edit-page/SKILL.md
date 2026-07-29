---
name: edit-page
description: Update an existing native Unbounce page in place — keeping its id, URL, stats, leads and integrations — by patching its element array. Requires the Unbounce MCP tools. Use when asked to change, fix, tweak or update copy, an image or geometry on a page that already exists in Unbounce, rather than rebuilding and re-uploading it. The tool pair is proven live (2026-07-29) but this skill's verification loop is not yet built — read this file fully before any write; a wrong-typed field value blanks the whole page.
---

# Edit a live page in place

## Status: the tool pair works. The P4 failure was a malformed patch, not the tool.

The two element-level tools this skill needs — `get_variant_elements` and
`set_variant_elements` — exist in the forked MCP (WP4) and the plugin pins them. **Both
halves are proven against a live variant** (P4 re-run, 2026-07-29, tag `v0.1.0-jf.1`):
unchanged round-trip, targeted text patch, and a `customClassnames` addition all rendered
pixel-perfect and the patched copy appeared live in the screenshot.

### The P4 blank page, root-caused 2026-07-29

The original P4 run patched `customClassnames` as an **array** (`["p4-probe-class"]`). The
field is a **string** (`"p4-probe-class"`) — format.md has always said so. A controlled
bisect on a throwaway page (same 115-element file, one change per write, screenshot after
each) proved this one wrong-typed field is the entire failure:

| Write | Render |
|---|---|
| Unchanged array, twice | ✅ perfect |
| Text patch only | ✅ perfect, new copy visible live |
| `customClassnames: ["…"]` (array) only | ❌ blank both breakpoints, editor can't load |
| Clean array written back over the blank page | ✅ **page fully restored** |
| `customClassnames: "…"` (string) only | ✅ perfect |

Three standing lessons:

1. **The write validates structure, not content.** `set_variant_elements` catches a corrupt
   *array* (duplicate ids, missing root, orphan containerId) but a wrong-typed *field value*
   sails through, Unbounce stores it without complaint, and the renderer and editor both die.
   The tool cannot protect you from a bad patch — only the format docs and a screenshot can.
2. **The damage is reversible with the same tool.** A blank page is not a lost page: re-write
   the last known-good array and it comes back. Keep the pre-patch read on disk until the
   screenshot passes — it is the undo button.
3. **An elements diff is necessary but never sufficient.** The original P4 diff was
   byte-identical while the page was blank. Any write to a variant must be verified by a
   **screenshot**, and blank is the failure mode to expect. Blank ≈ 27 KB desktop shot,
   healthy ≈ 382 KB — spottable without opening the image.

`set_variant_elements` stays guarded by `scripts/guard-native-page.py`: it overwrites a whole
live page with no server-side content validation, so a human should confirm the target every
time.

### One known wart in the fork's save path

Every save flips the variant's `autoscale` from `null` to `true`: `buildVariantXml` template-
interpolates `null` into the literal string `"null"`, which Unbounce's boolean cast reads as
true. Diffing the full `edit.json` before/after a write showed **this is the only stored field
a write mutates** (plus `updated_at`). It did not affect rendering on our pages, but it is an
unintended record change — fix in the fork when it's next touched (emit nothing when
`autoscale` is null), and re-check with the same before/after `edit.json` diff. The empty
`<name>` the XML sends in its `<page>` block is ignored by the server — verified no-op.

**What not to do:** `edit_variant` looks like the tool for this and is not. It overwrites the
**first `lp-code` element it finds** — on our pages, a 32px icon embed — so it destroys
decoration and never touches the copy you meant to change. `deploy_page` is worse: it
replaces the page body with one `lp-code` blob. Both are banned on native pages. The element
tool pair is the only correct route.

## The flow

1. **Fresh read, every session.** `get_variant_elements` at the start of the work, never a
   cached or remembered array. The client editing the page in the UI between sessions is the
   normal state, not an edge case — patching a stale array would silently revert their work.
   **Keep this read on disk untouched until step 4 passes — it is the undo button.**
2. **Patch locally.** Copy, geometry, classes. Geometry obeys the same grid the design does.
   Every patched field must match the shape format.md documents — a wrong-typed value
   (P4's array-for-string `customClassnames`) is stored without complaint and blanks the page.
3. **Write back** the whole array with `set_variant_elements`.
4. **Re-read and diff** to confirm what landed — `scripts/diff_elements.py before.json
   after.json` (strict mode; expect exactly your patch, nothing else) — **and screenshot,
   always.** P4 proved the diff can be perfect while the page is blank. The screenshot is
   not a nice-to-have. If it comes back blank, write the step-1 array back and screenshot
   again — that restores the page.
5. **Never publish.** The client publishes in the UI.

Step 4's screenshot is the part P4 turned from a formality into a hard requirement.

## What the two tools actually do, for whoever picks up WP5

Both live in `journey-further/unbounce-mcp`, pinned by tag in the plugin's `.mcp.json`.

- `get_variant_elements(sub_account_id, page_id, variant, output_file_path?)` — returns the
  variant's `elements` array verbatim, plus `count`, `last_element_id` and a per-type tally.
  **Always pass `output_file_path`.** A real page is ~150 KB of JSON, around 40k tokens; the
  array is for a script to diff, not for the context window.
- `set_variant_elements(sub_account_id, page_id, variant, elements | elements_file_path)` —
  replaces the whole array. It refuses one that is empty, has duplicate or missing ids, has
  anything other than exactly one `lp-pom-root`, or carries a `containerId` naming an element
  that isn't in the array. Those checks are structural only: they catch a corrupt array, not a
  wrong one. Geometry, content shape and mobile flags are still entirely on the caller.

`last_element_id` is raised automatically to match the highest id written, so the editor won't
later hand out a colliding id. The save rebuilds the whole variant record, not just `elements` —
verified consequence today: only the `autoscale` wart above; everything else round-trips
unchanged.

## What import does to a page (P3, answered 2026-07-29)

Diffing a `.unbounce`'s own `elements.json` against `get_variant_elements` right after upload,
Unbounce rewrites far less than WP5 assumed:

- **Element ids survive.** Not rewritten. `lp-pom-text-31` stays `lp-pom-text-31`.
- **Geometry survives exactly.** The only change is `70.0` → `70` — a float-to-int type
  coercion with identical numeric values. Compare numerically, never by type.
- **No timestamps are rewritten.** There were none to rewrite.
- **Asset references are rewritten**, and only these: `content.asset.uuid`,
  `content.asset.content_url` and `content.asset.unique_url` get fresh account-scoped values,
  and a numeric `content.asset.id` is **added**. Filenames are preserved. Confirms D3 — keep
  bundling assets in the tarball.

So a differ needs to normalise exactly two things: numeric type coercion, and those four
`content.asset.*` keys. That is the whole normalisation list — and it is only needed when
comparing *across an import*. For a read → patch → write → re-read cycle no normalisation is
needed at all, because that round-trip is byte-identical.
