---
name: upload-page
description: Upload a packaged .unbounce file into an Unbounce account as an unpublished page, then verify the real render — screenshot and preview link. Requires the Unbounce MCP tools. Use when asked to upload, push, deploy or get an .unbounce file into Unbounce, to put a built page in the account, or to produce a preview link for a page file.
---

# Upload an .unbounce file

Input: an existing `.unbounce` file on disk. Output: an **unpublished** page in the account,
verified against a real render, plus a shareable preview link.

You did not necessarily build the file, and it doesn't matter. If the file is broken, that's a
`build-page` problem, not something to patch here.

## Before you start

You need the sub-account id — every tool below requires `sub_account_id`. `list_accounts` and
`list_sub_accounts` give it; `list_domains` gives the domain options.

**First run in a session opens a browser for Unbounce login** (SSO/2FA) and waits. That is
normal. Its Playwright needs its own chromium build installed through the MCP's own CLI — a
bare `npx playwright install chromium` fetches whatever build the *local* Playwright maps to,
which is not necessarily the one the MCP asks for.

## Do this

**1 · Upload, unpublished.**

```
upload_unbounce_file(
  unbounce_file_path = "/abs/path/out.unbounce",
  sub_account_id     = "…",
  domain             = "…",
  slug               = "…",
  publish            = false        ← ALWAYS pass it. The parameter defaults to TRUE.
)
```

- **`publish: false` is not optional and not the default.** Omitting it publishes to a live
  domain. See the rules below.
- The **page name baked into the file wins** over the `page_name` argument, so don't expect
  `page_name` to rename anything. Name the page in `build-page`'s `--page-name`.
- Uploading a second page for the same design needs a **distinct slug and name** — collisions
  with an existing page are the common first failure.

**2 · Fix up traffic mode.** A single-variant upload frequently lands in **weighted A/B
routing**. The `traffic_mode` upload argument only offers `ab_test` and `smart_traffic`, so
"all traffic to variant a" is a separate call: `set_traffic_mode(mode = "standard",
variant_id = "a")`.

> **Known gotcha:** on a single-variant upload, `set_traffic_mode` can come back as
> `Unauthorized` inside the upload's `pending_steps`. **Re-run the pending step. Do not
> re-upload** — you'll end up with two pages. With one variant at weight 100 the failure is
> usually cosmetic anyway (all traffic goes there regardless), so if the re-run also fails,
> note it in the handover and move on rather than chasing it.

**3 · Verify the real render.** The upload succeeding tells you nothing about how the page
looks.

- `get_page_variants(page_id)` → confirm the variant letters and weights are what you expect.
- **Elements round-trip** (when the element tools are available): `get_variant_elements` with
  an `output_file_path`, then
  `skills/edit-page/scripts/diff_elements.py --import <elements.json from the .unbounce> <downloaded.json>`.
  Clean exit means Unbounce stored exactly what was built — `--import` ignores the four
  `content.asset.*` keys import legitimately rewrites, and nothing else. (Named cross-skill
  exception, like build-page's `measure.mjs`: shared verification, not operating knowledge.)
- `screenshot_variant(page_id, variant, source = "preview")` → **two** full-page renders, not
  one: desktop at 1280px and mobile at 390px. It takes no viewport parameter because it does
  not need one — the breakpoint pair is automatic. Verified 2026-07-29.
  `source: "published"` is faster but only works on a published page, which ours never is.
- Walk **both** screenshots against the design: every block present, nothing overlapping, no
  collapsed section, and the mobile reflow is the one the `@media` block describes.

**Mobile is covered by the automated pass, with one caveat.** The mobile shot renders at
**390px** while the design contract authors mobile geometry at **320px**, so text sits in a
narrower box than it was measured for and long labels wrap one line further than expected.
Judge overlap and reflow from it; don't read a tight wrap as a defect without checking the
320px measurement. A real phone remains the only proof against the three render-breakers
(`multipleBreakpointsEnabled`, `hasLightbox`, string `scale`), which present as "fine in the
editor, broken on a device" — see the note on that in the repo `CLAUDE.md`.

**4 · Hand over the link.** `get_variant_preview_url(page_id, variant)` returns two URLs:
`share_url` for the user (an `app.unbounce.com` link, works while unpublished) and
`preview_url` for your own inspection. Give the user the `share_url`, the page id, and what
you checked.

Publishing is the client's move, in the UI.

## Banned tools — never on a native page

| Tool | Why |
|---|---|
| `deploy_page` | Packages the whole page body into **one `lp-code` element**. This is the exact failure the plugin exists to avoid. It is for raw HTML pages; ours are not. |
| `edit_variant` | Overwrites the **first `lp-code` element it finds**. On our pages that's a 32px icon embed, so it silently destroys decoration and doesn't touch the copy you meant to change. |

Editing a page in place is `edit-page`'s job, through element-level tools.

**A hook enforces this**, so the table above is not the only thing standing in the way:
`hooks/hooks.json` matches either tool under any MCP server name and escalates the call to
the user with the reason. It escalates rather than refuses, because both tools are correct on
an *MCP-managed* HTML/CSS page and the tool input alone doesn't reveal which kind of page is
being targeted. If you see that prompt on a page this plugin built, the answer is no.

## Rules

1. **Never publish.** Every upload is `publish: false`; the client reviews in the UI and
   publishes there. Publishing is an outward-facing action on a client's domain and is not
   ours to take.
2. **No mutate operation on a page carrying live traffic.** Check before touching anything you
   didn't just create.
3. **Throwaway pages get a prefixed name and get deleted.** Probes are not left lying around
   in a client's account.
4. **Report the page id and slug** every time. Without them the next session can't find what
   you made.
5. **A validation or render failure goes back to the design**, not into a fix here. This skill
   uploads and verifies; it does not repair pages.

## What this skill does not do

Stats, insights, leads, A/B analysis — out of scope. Page construction and correctness only.
