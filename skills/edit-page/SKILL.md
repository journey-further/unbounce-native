---
name: edit-page
description: Update an existing native Unbounce page in place — keeping its id, URL, stats, leads and integrations — by patching its element array. Requires the Unbounce MCP tools. Use when asked to change, fix, tweak or update copy, an image or geometry on a page that already exists in Unbounce, rather than rebuilding and re-uploading it. NOT YET AVAILABLE: read this file before attempting anything, it explains what to do instead.
---

# Edit a live page in place

## Status: blocked. Do not improvise around this.

The two element-level tools this skill needs — `get_variant_elements` and
`set_variant_elements` — exist in the forked MCP (WP4) and the plugin pins them. **The read
half is proven correct. The write half is proven BROKEN and must not be pointed at any page
you care about.**

### P4 result, 2026-07-29 — the write breaks the render

Probed on a throwaway page built from a real 115-element native page (5 images, 22 nested
boxes, a form, a form-confirmation sub-page), against the pinned tag `v0.1.0-jf.1`:

| Check | Result |
|---|---|
| `get_variant_elements` after import | ✅ 115 elements, correct type tally |
| Write the array back **unchanged**, re-read | ✅ **byte-identical** |
| Patch one string + add one `customClassnames`, re-read | ✅ exactly those 2 field diffs, nothing else |
| **Screenshot the page after the write** | ❌ **completely blank, both breakpoints** |
| **Open the written page in the Unbounce editor** | ❌ **"Unable to load your page"** |
| Same file uploaded to a second page, never written | ✅ renders perfectly |

**The damage is unrecoverable.** The editor cannot open the variant, so there is no "just fix
it in the UI" path — and `get_variant_elements` still reads the array back fine, so the array
is not where the corruption is. A `set_variant_elements` call against a page anyone needs
loses that page. `set_variant_elements` is therefore guarded by
`scripts/guard-native-page.py` alongside `deploy_page` and `edit_variant`.

So the data layer is flawless and the page is dead. The control upload proves the import path
is fine and the *write* is what blanked it. Re-screenshotting later ruled out a recompile
delay.

**⚠️ The methodological lesson, which matters more than the bug.** A diff-based check —
including the `diff_elements.py` that WP5 specifies — **passes this failure**. The array is
byte-identical; there is nothing for a differ to find. Only the screenshot caught it. So:

> **An elements diff is necessary but never sufficient. Any write to a variant must be
> verified by a screenshot as well, and a blank render is the failure mode to expect.**

Blank vs healthy is easy to spot without looking: the blank desktop shot came back at 27 KB,
the healthy one at 382 KB.

### Where the bug is

Not in Unbounce and not in the element array — in the fork's save payload. `directSetVariantElements`
(`src/direct.js`) patches `raw.elements` and then rebuilds the *whole* save body with
`buildSaveXml` → `buildVariantXml`, which re-serialises a **fixed list** of variant fields
(`settings`, `autoscale`, `version`, `has_form`, `open_graph`, `favicon`, the sub-page tree…).
Anything the editor needs that is absent or differently-named in the `edit.json` response
serialises to an empty CDATA or the literal string `undefined` and is written back over good
data. Named suspects, in order:

1. **`settings`** — carries `defaultWidth` and `multipleBreakpointsEnabled`. Wiping it would
   plausibly produce exactly this blank render.
2. **The sub-page tree** — `buildVariantXml` is reused for each entry of `fullResponse.subPages`,
   and sub-page objects may not have the same shape as `mainPage`. Our pages always ship one
   sub-page (the form confirmation); the comment on `buildSaveXml` ("must include both mainPage
   and subPages to avoid 500 errors") says this area already bit someone.

The fix is a fork change plus a re-probe, not a change here. **Until that lands this skill
stays blocked** — the failure looks like our bug rather than an Unbounce limitation, so
`edit-page` is *deferred*, not withdrawn.

**What to do instead, today:** rebuild the page with `design-page` → `build-page` and upload
it as a new page with `upload-page`. Say plainly that the page id, URL, stats, leads and
integrations do not carry over, because with a fresh upload they don't. That is the honest
answer and it is the one to give.

**What not to do:** `edit_variant` looks like the tool for this and is not. It overwrites the
**first `lp-code` element it finds** — on our pages, a 32px icon embed — so it destroys
decoration and never touches the copy you meant to change. `deploy_page` is worse: it
replaces the page body with one `lp-code` blob. Both are banned on native pages. There is no
third option hiding in the MCP; if there were, this skill would already work.

## The intended flow, for when the tools land

1. **Fresh read, every session.** `get_variant_elements` at the start of the work, never a
   cached or remembered array. The client editing the page in the UI between sessions is the
   normal state, not an edge case — patching a stale array would silently revert their work.
2. **Patch locally.** Copy, geometry, classes. Geometry obeys the same grid the design does.
3. **Write back** the whole array with `set_variant_elements`.
4. **Re-read and diff** to confirm what landed — **and screenshot, always.** P4 proved the
   diff can be perfect while the page is blank. The screenshot is not a nice-to-have.
5. **Never publish.** The client publishes in the UI.

That is the shape, not instructions. Step 4's screenshot is the part P4 turned from a
formality into a hard requirement.

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
later hand out a colliding id. **"Nothing else about the variant is touched" is what the tool
intends and not what it does** — see the P4 result above; the save rewrites every variant field,
not just `elements`.

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
