# SPEC-v2 — implementation spec

Status: **ready to implement**. Scope and decisions live in `PLAN-v2.md` (agreed
2026-07-28); shape decisions in `docs/adr/0001` (MCP fork) and `docs/adr/0002` (skill
split). This file is the executable version: what to change, where, and how to know it
worked. Written for an implementing agent starting cold.

File paths and line numbers below were validated against the codebase on 2026-07-28.
Anything marked **[verify]** could not be validated from this repo (upstream MCP internals,
plugin-manifest mechanics) and must be checked before use, not assumed.

## Ground rules — govern every work package

1. **Native elements, never a raw-HTML blob.** Per element, not per page: a 32px icon
   `lp-code` is fine, a page-shaped one is the failure this repo exists to avoid.
2. **The transcriber never adjusts geometry.** Off-grid/off-canvas is a design error.
3. **Unproven means refuse.** No emitting guessed shapes. New platform facts come from the
   probe loop (generate varied page → upload → download → diff) and are written into a
   reference doc immediately — the references are the persistence layer.
4. **No connected/baseline branch inside any skill.** Connected capability = whole skills
   (`upload-page`, `edit-page`) that don't function without the MCP tools. No skill ever
   asks "am I connected?".
5. **Nothing client-specific or brand-specific enters a tracked path.** `ridgeline/` is
   untracked evidence; read it, never copy from it.
6. **The MCP never publishes.** Every upload is `publish: false`; the client checks in the
   UI and publishes there. No mutate operation targets a page with live traffic (none exists
   today — revisit per PLAN-v2 D7 the moment a domain is genuinely connected).

## Current state (validated 2026-07-28)

```
.claude-plugin/marketplace.json     marketplace "journey-further", plugin "unbounce-native", source ./
.claude-plugin/plugin.json          v0.1.0
agents/{brand-extract,mobile-derive,build-pack}.md
skills/design-page/SKILL.md         steps 1–6: brand → design → measure → mobile → transcribe → report
skills/design-page/references/{design-rules,grid,format,ui-capabilities}.md
skills/design-page/scripts/{transcribe.py,geometry.py,measure.mjs,test_transcribe.py}
package.json                        devDependency playwright (measure.mjs only; transcriber is stdlib-only)
```

Transcriber facts the work below touches: `INPUT_LPTYPE` at `transcribe.py:32` (text/email/tel
only); `select`/`textarea` refused at `:120`; `customClassnames` emission at `:246-256`;
`webFontsExternalInUse` always `{}` at `:652`; `hasLightbox: False` at `:656`; form fields
filtered to `INPUT_LPTYPE` membership at `:860-865`.

Branch state: work happens on `dev`; `origin/main` (what the public sees) predates the
bakeoff fixes and the `unbounce-page` → `design-page` rename. Note *local* `main` is one
unpushed commit ahead of `origin/main` (it has the rename) — don't trust local `main` as a
picture of what the client would install. Do not merge until WP6 says so.

---

## WP1 · Skill split (PLAN-v2 Phase 1 · ADR 0002)

Split `skills/design-page/` into four skills. Files on disk are the inter-skill contract;
each skill must work with no memory of the others having run — including in a fresh session.

### Target layout

```
skills/design-page/                 steps 1–4 (brand → design → measure loop → mobile → sign-off)
  SKILL.md
  references/{design-rules,grid,ui-capabilities}.md
  scripts/{measure.mjs,geometry.py}
skills/build-page/                  design.html → out.unbounce (mechanical)
  SKILL.md
  references/format.md
  scripts/{transcribe.py,test_transcribe.py}
skills/upload-page/                 out.unbounce → page in the account (connected-only)
  SKILL.md
skills/edit-page/                   live page → same page, updated in place (connected-only)
  SKILL.md                          skeleton now; content lands in WP5
```

### Contracts

- `design-page` output = a working folder containing `design.html` with **measured heights
  written back and a stable re-measure** (the step-3 loop finished), plus the mobile
  `@media (max-width:600px)` block, plus the design report. Ends at user sign-off — it never
  transcribes. Must support **resume**: "pick up `design.html` and keep editing" is a
  first-class entry, stated in SKILL.md.
- `build-page` input = that `design.html`. Runs `transcribe.py`, which validates and refuses
  to write on hard error. Output = `out.unbounce` + the build report, including the
  **"Not in the file"** section and the baseline upload instructions (All Pages → "Upload an
  Unbounce Page", traffic mode off "weighted", check a real phone). Build must not open a
  design conversation; a validation failure is reported back as "the design is wrong", not
  fixed in place.
- `upload-page` input = an existing `.unbounce` file. Calls `upload_unbounce_file` with
  `publish: false` (**the parameter defaults to true — always pass it**; the page name inside
  the file overrides the `page_name` argument), then `get_page_variants` +
  `screenshot_variant` at both breakpoints, then `get_variant_preview_url` for the shareable
  link. Known gotcha to document in the skill: `set_traffic_mode` can return `Unauthorized`
  in `pending_steps` on a single-variant upload — re-run the pending step, don't re-upload.
  Includes the banned-tools table: `deploy_page` (packages the whole body into one `lp-code`)
  and `edit_variant` (overwrites the first `lp-code` it finds — on our pages, an icon) are
  **never called on a native page**.
- `edit-page` skeleton: name, description, and a body that states the flow (fresh read →
  patch → write back → screenshot) and that it is blocked on the WP4 tool pair. No
  aspirational detail that could read as working instructions.

### Mechanics

- Move files with `git mv` so history follows.
- Each SKILL.md frontmatter `description` must carry its own trigger phrases (the current
  design-page description covers all four jobs; split it so "upload this .unbounce" routes
  to `upload-page`, "change the headline on the live page" routes to `edit-page`, etc.).
- Distribute the current hard-rules list to where each rule is enforced (1:1 isomorphism,
  nine primitives, one form → design-page and build-page; the three mobile flags, stylesheet
  classes-not-ids → build-page; banned tools → upload-page/edit-page; brand-as-input,
  CRO-out-of-scope → design-page). No rule may be lost in the split; duplicating a one-line
  rule in two skills is acceptable, a shared "doctrine" doc is not required.
- Cross-skill file reads use repo-relative paths (e.g. build-page's docs may cite
  `skills/design-page/references/grid.md` for context); each skill's *operating* knowledge
  must live in its own directory.
- **Agents stay in `agents/` at the plugin root** (that is where the plugin manifest finds
  them) but each is owned by one skill and WP1 must update their script paths: `brand-extract`
  and `mobile-derive` belong to design-page; `build-pack` belongs to build-page.
  `mobile-derive` currently invokes `transcribe.py` as a validation probe — after the move
  that path is `skills/build-page/scripts/transcribe.py`. `build-pack` runs both `measure.mjs`
  (design-page) and `transcribe.py` (build-page); its `measure.mjs` call is a **named
  cross-skill exception** — a final verification, not operating knowledge — and keeps the
  full `skills/design-page/scripts/measure.mjs` path.
- Update stale paths: repo `CLAUDE.md` (test command), `README.md`, `agents/*.md` (above),
  and any reference-doc cross-links. Check: `grep -rn
  "design-page/scripts/transcribe\|design-page/scripts/test_transcribe\|design-page/references/format"
  --include="*.md" .` must return nothing outside `SPEC-v2.md`/`PLAN-v2.md` (historical
  documents; they keep their original citations).

### Done when

- `python3 skills/build-page/scripts/test_transcribe.py` passes from the new location.
- A fresh session can run each skill from its SKILL.md alone: design → sign-off with no
  build; build from a `design.html` it didn't create; upload from an `.unbounce` it didn't
  build.
- No SKILL.md contains a connected/baseline conditional.

## WP2 · Probes P1, P2, P5 + resulting changes (Phase 1)

Findings from all three go back to the stakeholder as one batch (client comms, not tracked
in this repo). Every platform fact discovered lands in a reference doc in the same commit as
the probe conclusion.

### P1 — hidden form field (highest priority; blocks requirement 1)

Method: on a scratch page in the editor, add a non-visible field to a form, download the
page file, read the page JSON. No credentials needed. Capture: the field's `lpType`, its
JSON shape, and whether it participates in the 80px field stride and the label budget or
sits outside the laid-out stack.

Then implement: `<input type="hidden">` accepted in the design contract
(`design-rules.md` form section), mapped in `INPUT_LPTYPE` (`transcribe.py:32`) or a
dedicated emission path if the shape demands one (geometry participation decides which), a
`test_transcribe.py` case, and the fact recorded in `format.md`. If the editor offers no
such field type, the finding is "not expressible natively" — record it, refuse it in the
transcriber with a clear message, and requirement 1 falls back to the domain-level script
writing into a *visible-but-styled-hidden* field only if a probe proves that shape too;
otherwise it's refused in the handover with the reason.

No shortcut exists: both real exports in `ridgeline/` were checked (2026-07-28) and contain
no hidden-field shape — the probe is genuinely required. The handover answer for
requirement 1 should also mention Unbounce's native Dynamic Text Replacement
(`set_dynamic_text` in the MCP): it covers URL-param → *page copy* personalisation natively,
which may be part of what the stakeholder actually wants — it does not write into the lead
record, so it complements P1 rather than replacing it.

### P2 — class-triggered global lightbox vs `hasLightbox: false`

Method: build a minimal page whose button carries the agreed class (via `class="…"` in the
design HTML — the `customClassnames` path at `transcribe.py:246-256` already ships it),
define a global lightbox in the account settings, publish to a throwaway slug, test on a
real phone. Two manual steps here, by design: defining the global lightbox is an
account-admin action done in the UI, and **the publish is done by a human in the UI** —
ground rule 6 (the MCP never publishes) stands; it is safe because the domain carries no
live traffic (D7). The question: does the global dialog fire on a page built with
`hasLightbox: false` (`transcribe.py:656`)? That flag is load-bearing — `true` without a
lightbox sub-page tree collapses the live mobile render (see `ui-capabilities.md`).

Outcomes: fires → write the recipe into `ui-capabilities.md` and reference it from
upload-page/edit-page; requires the flag → requirement 2 is refused as automated capability,
documented as "dialog added in the editor", and the handover says so with the reason.

### P5 — icon-set integration (blocks nothing; close it honestly)

Two halves: confirm the SVG-as-`lp-code` route renders live (the V2 upload screenshots from
2026-07-28 may already answer this — check before building a probe), and determine whether
`webFontsExternalInUse` (`transcribe.py:652`, always empty) is a real hook for a non-Google
font CDN or vestigial — one probe page with an external icon font settles it. Record the
answer in `ui-capabilities.md` as an explicit "icons: SVG yes / icon fonts …" entry. An icon
*set preference* (e.g. Font Awesome) is a per-client convention → WP3 template slot, not
plugin content.

## WP3 · Convention template + standing constraints (Phase 1 · D6, D8)

- Create `templates/client-setup/CLAUDE.md` — client-neutral, commented slots, the template
  *is* the documentation. Slots: brand token source; per-brand domains; domain-level scripts
  (the URL-param → hidden-field script lives here once P1 lands); mandatory form fields;
  widget embeds (review widgets etc., pasted as the client's own snippet); icon set; anything
  the client wants on every page. One folder per brand — say so in the header comment.
- Add a short standing-constraints section to the repo `CLAUDE.md` (D8): the two states
  (baseline = create-only, no credentials; connected = the MCP fork per ADR 0001); the D5
  scope line (page construction and correctness here — stats, insights, leads, and add-on
  design tooling are per-client enhancements, never shipped from this repo); the
  MCP-never-publishes norm; connected capability arrives only as whole skills (ADR 0002).

Done when a stranger could copy the template into a new brand folder and fill it in without
asking anything.

## WP4 · The MCP fork + element pair (Phase 2 · D1, D2 · ADR 0001)

1. Fork `github.com/cgilchrist/unbounce-mcp` → `journey-further/unbounce-mcp`. A fork on
   GitHub is the legally clean route (upstream has no licence); do **not** copy code into
   this repo.
2. Add two tools in the fork — both halves already exist internally (verified 2026-07-28
   against the clone): `fetchVariantState` (`src/direct.js:455`) parses the element array
   out of `edit.json`; `directEditVariant` (`src/direct.js:531`) fetches the array, patches
   it in memory, then writes the **whole array** back (`raw.elements = JSON.stringify(...)`
   → `save.xml`). So `set_variant_elements` is directEditVariant with the lp-code-targeting
   middle removed — the write-back tail is reused as-is.
   - `get_variant_elements(page_id, variant)` → the raw elements array, unfiltered — bypass
     the Classic Builder classification that makes `get_variant` return a preview instead.
   - `set_variant_elements(page_id, variant, elements)` → writes the whole array. Must not
     reuse `edit_variant`'s first-`lp-code` targeting.
3. Open the upstream PR with both tools, and ask the licence question in the PR body — a
   grant is what would unlock vendoring later.
4. Wire the fork into the plugin so the client installs one thing (mechanism verified
   against current Claude Code plugin docs, 2026-07-28 — see
   code.claude.com/docs/en/plugins-reference.md §MCP servers, §User configuration):
   - **Plugin-root `.mcp.json`** (sibling to `skills/`, not inside `.claude-plugin/`), same
     schema as a project `.mcp.json`. Plugin MCP servers start automatically when the plugin
     is enabled — no `claude mcp add`.
   - **API key via `userConfig` in `plugin.json`**, not a raw env var: a field with
     `"sensitive": true` makes Claude Code prompt for it (masked) at plugin enable, store it
     in the keychain, and inject it via `"env": {"UNBOUNCE_API_KEY":
     "${user_config.unbounce_api_key}"}` in the server config. This is the zero-manual-setup
     path.
   - **Pin the fork explicitly** in `args` (npm version or git tag/SHA) — the plugin's own
     `version` field does not pin what `npx` resolves at server start.
   - **`npx github:org/repo` as the server command is undocumented for plugin MCP configs**
     — unproven means refuse: probe it (fresh install in a clean checkout, confirm the tools
     appear in `/mcp`) before it becomes the documented install path; publishing the fork to
     npm is the fallback if it misbehaves.
   - **Leave `alwaysLoad` unset**: MCP startup is non-blocking by default, so a failed
     server start (no key, offline) just means the connected skills' tools are absent —
     exactly the ADR 0002 model; baseline is untouched.
   - Iteration note: `.mcp.json` edits need `/reload-plugins` or a restart, no hot reload.

   First-run note for docs: the MCP's Playwright needs its own chromium build (1234 for
   Playwright 1.62.0), installed via the MCP's own CLI, not a bare
   `npx playwright install chromium`.

Done when: on a throwaway page (prefixed name, deleted after), `get_variant_elements` →
`set_variant_elements` with the array unchanged → `get_variant_elements` again returns an
equal array, and a fresh `claude` session in a clean checkout sees the tools with no manual
`claude mcp add`.

## WP5 · Mutate probes + `edit-page` (Phase 2 · P3, P4, D3)

Order matters: **P4 first — it is the kill-shot.** If a written array does not survive, the
mutate loop is dead regardless of tooling: `edit-page` is withdrawn, handover reverts to
create-only, and PLAN-v2 + ADR 0002 get a dated note. Everything else in this WP assumes P4
passed.

- **P4 — does a written array survive?** Read a throwaway page's elements, change one
  string, write, re-read, diff (expect only the string). Then open the page in the editor,
  save, re-read, diff again (expect geometry, custom classes and asset references intact).
- **P3 — what does import do to asset references?** Upload a fresh `.unbounce`, read the
  elements back, diff against what `transcribe.py` emitted. Expected: ids, asset UUIDs and
  timestamps rewritten; shapes and geometry intact. Record the actual rewrite behaviour in
  `format.md`; it confirms D3 (keep bundling; `upload_image` only for images *new to an
  update*, element rewritten to the returned CDN URL).
- **Diff tooling:** `skills/edit-page/scripts/diff_elements.py` — stdlib-only, takes two
  element-array JSON files, normalises the known-rewritten keys (ids, asset UUIDs,
  timestamps — as found by P3), diffs shapes and geometry, non-zero exit on real drift. The
  agent fetches the arrays via the MCP tools; the script only compares. This is the
  "round-trip probe runs as a command" line in the definition of done — upload-page's
  verification step uses the same script (a **named cross-skill exception**, like
  build-pack's `measure.mjs` call: shared verification, not operating knowledge).
- **Go back and upgrade `upload-page`:** its WP1 version verifies by screenshot only,
  because the element tools don't exist yet. Once P3/P4 pass, add the elements round-trip
  (`get_variant_elements` → `diff_elements.py` against what `transcribe.py` emitted) as
  upload-page's verification step.
- **`edit-page` SKILL.md content** (replacing the WP1 skeleton): every session starts with a
  fresh `get_variant_elements` — never patch from a cached array; the client editing in the
  UI is the normal state, not an edge case. Patch locally (copy, geometry, classes); a *new*
  image goes through `upload_image` first and the element points at the returned CDN URL.
  Write back with `set_variant_elements`, re-read and `diff_elements.py` to confirm, then
  `screenshot_variant` both breakpoints. Never publish. Geometry discipline carries over:
  patched positions obey the same grid; `skills/design-page/scripts/geometry.py snap` gives
  legal values.

## WP6 · Prove, merge, hand over (Phase 3)

1. **Merge `dev` → `main` and push.** Everything the client installs comes from
   `origin/main`; before the merge-and-push they'd get a stale skill name (local `main` is
   already ahead of `origin/main` — pushing the merge covers both). Bump `plugin.json` from
   0.1.0 and tag the merge commit, so "what was handed over" has a name.
2. **Cold-start acceptance run, by us:** fresh context (the no-CLAUDE.md/no-memory session
   recipe), design brief + brand tokens only — ideally a real brief requested from the
   client. The full protocol, including the three-tier run and what to watch for, is the
   "Prove v1 end-to-end from a cold start" entry in `BACKLOG.md`; it applies unchanged, plus
   one addition: **demonstrate the mutate loop once end to end** (build → upload → edit one
   string via `edit-page` → same page id, change visible in the screenshot).
3. **Handover pack** (client comms, not tracked here): the marketplace install command, API
   key → env instruction, **first-run connected-mode steps** — the MCP opens a browser for
   Unbounce login (SSO/2FA) on first use, and its chromium must be installed via the MCP's
   own Playwright CLI (build 1234 for Playwright 1.62.0), not a bare `npx playwright install`
   (both bit us on 2026-07-28) — a copy of `templates/client-setup/CLAUDE.md` started for
   their brand, and the probe findings — with requirements 1 and 2 each either *supported*
   (here's how) or *refused* (here's why), never silent.

## WP7 · Variants (Phase 4 — do not start until WP5 is proven)

`duplicate_variant` (server-side, safe) → patch the copy via the WP4/WP5 machinery →
`rename_variant` → `set_variant_weights`. Bolts onto `edit-page`; not handover-blocking.
Cheaper than it looks: upstream already ships `directDuplicateVariant`,
`directCreateVariantFromScratch` and `directInitBlankSlate` (`src/direct.js:323/:976/:920`)
— no new machinery, only the probe. Which variant to *test* is CRO and stays out of scope.
Spec this properly when it starts — one probe (does a duplicated variant read/write cleanly
through the pair?) before any skill text.

---

## Definition of done (from PLAN-v2, restated)

- Baseline still works with no credentials and no network beyond design-time measurement.
- A page built by the plugin can be updated in place without losing its id, URL, stats,
  leads or integrations.
- The round-trip probe runs as a command (`diff_elements.py`), not a manual browser session.
- Requirements 1 and 2 (hidden fields, global lightbox) are each supported or explicitly
  refused in the handover, with the reason.
- No skill contains a connected/baseline branch; connected capability exists only as
  `upload-page` and `edit-page`.
- A design resumes across sessions; `build-page` runs from a design it did not create.
- Nothing client-specific or brand-specific has entered a tracked path.
