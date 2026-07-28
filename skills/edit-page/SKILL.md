---
name: edit-page
description: Update an existing native Unbounce page in place — keeping its id, URL, stats, leads and integrations — by patching its element array. Requires the Unbounce MCP tools. Use when asked to change, fix, tweak or update copy, an image or geometry on a page that already exists in Unbounce, rather than rebuilding and re-uploading it. NOT YET AVAILABLE: read this file before attempting anything, it explains what to do instead.
---

# Edit a live page in place

## Status: blocked. Do not improvise around this.

In-place editing needs two element-level MCP tools that **do not exist yet**:
`get_variant_elements` and `set_variant_elements` (SPEC-v2 WP4). Until they ship in the
forked MCP and the round-trip probes pass (WP5), this skill cannot do its job.

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

That is the shape, not instructions — the tools, the diff step and the probe evidence all
come in WP4/WP5. When they do, this file gets replaced with the real thing.
