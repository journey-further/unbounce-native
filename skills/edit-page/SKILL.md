---
name: edit-page
description: Update an existing native Unbounce page in place — keeping its id, URL, stats, leads and integrations — by patching its element array. Requires the Unbounce MCP tools. Use when asked to change, fix, tweak or update copy, an image or geometry on a page that already exists in Unbounce, rather than rebuilding and re-uploading it. NOT YET AVAILABLE: read this file before attempting anything, it explains what to do instead.
---

# Edit a live page in place

## Status: blocked. Do not improvise around this.

The two element-level tools this skill needs — `get_variant_elements` and
`set_variant_elements` — now exist in the forked MCP (WP4, 2026-07-28) and the plugin pins
them. **The read half is safe to use. The write half is unproven and must not be pointed at a
real page yet.**

What is missing is WP5: nobody has yet written an array back to a live variant and read it
again to see what survived. Until that probe passes, an apparently-successful
`set_variant_elements` call could have silently dropped or rewritten parts of the page —
`publishedStyles` on a form is derived and recomputed by the editor, and asset references may
be rewritten on the way in. A write that looks fine and quietly mangles the page is the exact
failure this repo exists to avoid, so the answer is not "try it carefully on the client's
page".

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
4. **Re-read and diff** to confirm what landed, then screenshot the variant.
5. **Never publish.** The client publishes in the UI.

That is the shape, not instructions — the diff step and the probe evidence come in WP5. When
they land, this file gets replaced with the real thing.

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
later hand out a colliding id. Nothing else about the variant is touched.

The first WP5 probe is the kill-shot and should run on a **throwaway page, never a client
page**: upload a built `.unbounce`, read the array, write it straight back unchanged, read it
again, and diff. If an unchanged round-trip isn't byte-identical, find out what changed it
before attempting any real edit.
