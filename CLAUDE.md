# unbounce-native — repo notes

A Claude Code plugin that builds natively-editable Unbounce landing pages. See `README.md`
for what it is; the four skills under `skills/` are how it works —
`design-page` → `build-page` → `upload-page`, plus `edit-page`.

## Working in here

- **This repo is client-shippable.** Nothing brand-specific, client-specific or CRO-related
  gets tracked. Brand is an input resolved by `agents/brand-extract.md`; CRO stays in
  Journey Further's internal tooling.
- `ridgeline/` is the **untracked** working directory from the project this came out of —
  the design source, the earlier generator, both real Unbounce exports, and the long-form
  format notes. It is gitignored on purpose: it's the evidence base, not the deliverable.
  Read it freely; never move anything from it into a tracked path.
- The reference docs under `skills/*/references/` are the persistence layer. If you learn a
  platform fact, it goes there **in the same commit** or it's lost — that's what makes a
  cold-start session possible.
- Run `python3 skills/build-page/scripts/test_transcribe.py` after touching the transcriber.
  Note `design-page`'s `geometry.py` imports `BP` from the transcriber, so the grid constants
  stay single-source across the two skills — that import is deliberate, don't break it by
  duplicating the constant.

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
`skills/build-page/references/format.md` was found.

## Standing constraints

- **Two states, no middle.** *Baseline* is create-only and needs no credentials and no network
  beyond design-time measurement (`design-page`, `build-page`). *Connected* adds the Unbounce
  MCP and, with it, `upload-page` and `edit-page`. See `docs/adr/0001-external-mcp-not-vendored.md`.
- **Connected capability arrives only as whole skills.** No skill contains an "am I connected?"
  branch — a skill either needs the MCP tools to function or never touches them. When the MCP
  isn't there, its tools are simply absent and baseline is unaffected.
  `docs/adr/0002-four-skills-split-at-session-boundaries.md`.
- **The MCP never publishes.** Every upload is `publish: false`. The client reviews in the UI
  and publishes there — it's their domain and their call.
- **Scope is page construction and correctness.** Stats, insights, leads, A/B analysis and
  add-on design tooling are per-client enhancements built elsewhere; they never ship from this
  repo.
- **Per-client conventions live in `templates/client-setup/`**, copied per brand into the
  client's own repo — never filled in here.
- **The three page-destroying tools are guarded, not just documented.**
  `hooks/hooks.json` + `scripts/guard-native-page.py` escalate `deploy_page`,
  `edit_variant` and — since the P4 failure on 2026-07-29 — `set_variant_elements` to the user. Matched by tool-name suffix (`mcp__.*__(deploy_page|edit_variant)`)
  so it fires under any server name — a plugin-bundled MCP scopes its tools as
  `mcp__plugin_<plugin>_<server>__<tool>`, and a matcher written against the bare server key
  never fires. It escalates rather than denies because both tools are correct on an
  MCP-managed HTML/CSS page. `permissions.deny` cannot do this job from here: a plugin's own
  `settings.json` honours only the `agent` and `subagentStatusLine` keys, and this repo's
  `.claude/` is gitignored. A deny list belongs in the *client's* repo — it's in the
  client-setup template.

## Status

v1 skeleton complete (2026-07-25): plugin manifests, skill + four reference docs, transcriber
with validators + tests, measure script, three agents. **Not yet proven end-to-end** — v1 is
done when the reference page has been rebuilt from a cold start (fresh context, design brief
+ brand tokens only) and the resulting `.unbounce` imports, renders correctly on a real
phone, and the client can drag a whole card as one unit.

v2 in progress (`SPEC-v2.md` is the executable plan, `PLAN-v2.md` the decisions).

Done: WP1 the four-skill split · WP3 the client-setup template and these constraints ·
WP2 P1 **hidden fields are supported** (shape proven from a purpose-built export, emitted and
tested) · **WP2 P5 closed** (2026-07-29) — inline SVG icons render live, and so do external
fonts: a stylesheet `<link>` in one `lp-code` is document-global, covering icon fonts *and*
non-Google faces on native text. `webFontsExternalInUse` is the editor's custom-font record,
not our hook; it stays `{}`. See `ui-capabilities.md` → *External fonts* · WP4 the element
tool pair and the plugin wiring · **WP5 closed** (2026-07-29) — the end-to-end edit-page run
passed against the live $2,500 page (fresh read → one-string patch → write → diff exact →
screenshot healthy → restore verified), and the editor-save probe passed the same day: a
human edit in the UI touched **only the edited element** across 161; the editor backfills
`content.fonts` on the element it re-serialises and adds a trailing `;` to inline styles —
expected noise when diffing across a client edit, never something to "correct" back. See
`skills/edit-page/SKILL.md`.

Outstanding: WP2 P2 Phase A (stakeholder confirmation of the Script Manager route — desk
work) · WP6 merge and cold-start acceptance. WP2 P2 Phase C and real-phone checks stay
blocked on the client's domain.

### WP5 probes, 2026-07-29 — P3 passed; P4 failed, then root-caused the same day

**P3 answered:** import rewrites almost nothing. Element ids survive, geometry survives (only
`70.0`→`70` type coercion), no timestamps change; **only** `content.asset.{uuid,content_url,unique_url}`
are rewritten and a numeric `content.asset.id` is added. Confirms D3 — keep bundling.

**P4's blank page was our malformed patch, not the fork.** The probe wrote `customClassnames`
as an **array**; the field is a **string** (format.md said so all along). A controlled bisect
(one change per write, screenshot after each) proved: unchanged round-trips, text patches and
string-typed `customClassnames` all render perfectly; the array-typed field alone blanks the
page and locks the editor out; **writing the clean array back restores the page** — the
damage is reversible, not fatal. Unbounce applies no content validation on save, so a
wrong-typed field value is the page-destroying class of mistake and only a screenshot catches
it. One genuine fork wart found by diffing the full `edit.json` before/after: every save
flips `autoscale` null→true (string `"null"` boolean-cast). Harmless to render; fix in the
fork when next touched. Full write-up in `skills/edit-page/SKILL.md`.

**The rule that came out of it, which outlives the bug:** an elements diff is necessary but
**never sufficient**. `diff_elements.py` as specced in SPEC-v2 would have passed this failure —
the array was byte-identical. Every write to a variant must be verified by a **screenshot** too.
Blank ≈ 27 KB, healthy ≈ 382 KB, so it is cheap to spot.

### The fork (WP4, 2026-07-28)

`get_variant_elements` / `set_variant_elements` live in `journey-further/unbounce-mcp` and the
plugin's root `.mcp.json` pins them by tag. Facts worth not rediscovering:

- **The fork's `master` is protected by an org ruleset** — direct pushes are declined, a PR
  with an approving review is required. The work therefore sits on the `feat/variant-elements`
  branch and the **tag `v0.1.0-jf.1`** is what `.mcp.json` resolves. `master` is still at
  upstream. Bumping the pin means a new tag, not a push to master.
- **`npx github:org/repo#tag` works as a plugin MCP command** — probed end to end (clean
  install, server starts, 46 tools listed including the new pair), so publishing the fork to
  npm isn't needed. The pin is deliberate: the plugin's own `version` does not constrain what
  `npx` resolves.
- **The API key is optional by design.** `userConfig.unbounce_api_key` has no `required: true`,
  so a baseline user installs, skips it, and designs and builds offline. Note the docs make
  `title` a required field on a `userConfig` option; SPEC-v2 omits it.
- **No upstream PR and no licence ask** — deliberate, per the 2026-07-28 decision. ADR 0001's
  "PR'd upstream in parallel" is the eventual intent, not a current task.
- **Both halves are proven against a live variant** (2026-07-29): reads are safe, and writes
  round-trip, apply targeted patches, and render correctly — provided every patched field
  matches its documented shape. Known wart: each save flips `autoscale` null→true.

**Blocked on the client, not on us** (2026-07-28): anything needing a published page or a real
device. The client has no domain set up, so P2 (global lightbox — also no admin access to
define one), real-phone render verification, and the v1 "renders correctly on a real phone"
acceptance criterion all wait for that. Don't plan work that assumes a publish; don't ask for
a phone check. Mobile verification is a 320px viewport on a preview URL until the domain
exists.
