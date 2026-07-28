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
- **The two page-flattening tools are guarded, not just documented.**
  `hooks/hooks.json` + `scripts/guard-native-page.py` escalate `deploy_page` and
  `edit_variant` to the user. Matched by tool-name suffix (`mcp__.*__(deploy_page|edit_variant)`)
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
tested) · WP2 P5 half — inline SVG icons render live · WP4 the element tool pair and the
plugin wiring.

Outstanding: WP5 mutate probes and a working `edit-page` · WP6 merge and cold-start
acceptance.

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
- The write half is **unproven against a live variant** — that is WP5, and `edit-page` stays
  blocked until it passes. The read half is safe.

**Blocked on the client, not on us** (2026-07-28): anything needing a published page or a real
device. The client has no domain set up, so P2 (global lightbox — also no admin access to
define one), real-phone render verification, and the v1 "renders correctly on a real phone"
acceptance criterion all wait for that. Don't plan work that assumes a publish; don't ask for
a phone check. Mobile verification is a 320px viewport on a preview URL until the domain
exists.
