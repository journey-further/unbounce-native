# unbounce-native

A Claude Code plugin that builds **natively-editable** Unbounce landing pages.

## The problem it solves

The usual way to get a design into Unbounce is to paste it into one Custom HTML element. The
page imports. The page looks right. The page is also dead to the drag-and-drop editor. Nobody
on the client team can change a headline, duplicate a card, or create a variant.

This plugin writes **real native `lp-pom-*` elements** instead. The client edits the page as
if somebody built it by hand in the editor.

One decision makes that affordable. The design is authored **tight to the Unbounce Classic
spec from the first pixel**: its canvas, its column grid, its 320px mobile cap. Turning the
design into a `.unbounce` file is then mechanical transcription, not a repair pass. There is
no reflow step, no height estimation, and no rebuild loop.

## Contents

1. [Before you install](#before-you-install)
2. [Install the plugin](#install-the-plugin)
3. [Connect an Unbounce account](#connect-an-unbounce-account-optional)
4. [Set up a folder for each brand](#set-up-a-folder-for-each-brand)
5. [Get the brand tokens in](#get-the-brand-tokens-in)
6. [Use it](#use-it)
7. [What is in the repo](#what-is-in-the-repo)
8. [Platform limits you need to know](#platform-limits-you-need-to-know)
9. [What it deliberately does not do](#what-it-deliberately-does-not-do)
10. [Troubleshooting](#troubleshooting)
11. [Tests](#tests)

## Before you install

| You need | For what | Notes |
|---|---|---|
| Claude Code | Everything | The plugin is skills plus scripts. It runs inside Claude Code. |
| Python 3 | Building the `.unbounce` file | Standard library only. No pip, no network. It works offline and in CI. |
| Node 18 or later, plus `npm install` in this repo | Measuring the design | This installs Playwright and Chromium. |
| Network access at design time | Measuring the design | Google Fonts must load, or the text metrics are wrong. |
| An Unbounce **Classic Builder** account | Uploading and editing | Smart Builder pages cannot be exported or imported at all. Check which builder the account uses before you start. |

Design and build need no Unbounce credentials. Only upload and edit do.

## Install the plugin

Run these two commands in Claude Code:

```
/plugin marketplace add journey-further/unbounce-native
/plugin install unbounce-native
```

The installer asks for an Unbounce API key. The key is optional. Read the next section before
you decide.

Then install the measurement dependency once. The design step measures text in a real browser,
and the script `measure.mjs` imports Playwright by name. So Node must resolve Playwright from
the script location. Run this in the installed plugin directory:

```bash
npm install
```

That command also downloads Chromium. If you do not know where the plugin directory is, ask
Claude to find it and run the command for you.

After that, ask for what you want in plain words. For example: *"build me an Unbounce landing
page for a roof replacement offer"*. The skills activate on their own. You do not call them by
name.

## Connect an Unbounce account (optional)

The plugin has two states, and there is nothing in between.

| State | What works | What it needs |
|---|---|---|
| **Baseline** | `design-page` and `build-page`. You get a finished `.unbounce` file on disk, which anybody can import by hand in the Unbounce UI. | Nothing. No API key and no account. |
| **Connected** | Also `upload-page`. The page goes into the account, unpublished, and Claude verifies the real render. | An Unbounce API key and a browser login. |

To connect, paste an Unbounce API key when the plugin asks for one at install. Get the key in
Unbounce under **Settings → API keys**. The key goes to your operating system keychain. It
never goes into this repo. Leave the field empty and everything except the connected skills
still works.

The plugin carries the MCP server itself. The file `.mcp.json` points at
[`journey-further/unbounce-mcp`](https://github.com/journey-further/unbounce-mcp), a fork of
[`cgilchrist/unbounce-mcp`](https://github.com/cgilchrist/unbounce-mcp). The fork adds the
`get_variant_elements` and `set_variant_elements` pair that a native page needs. The plugin
pins the fork to a tag, so an upgrade is a deliberate edit rather than whatever `npx` resolves
on the day.

Three things to know about the connected state:

1. **The first use in a session opens a browser window for an Unbounce login.** The API key
   alone does not cover the editor endpoints, so the server keeps a session in
   `~/.unbounce-mcp/session.json`. This step is interactive and nobody can automate it away.
   Expect single sign-on or two-factor authentication here.
2. **Remove any copy of this MCP that you added by hand.** If you ran `claude mcp add unbounce
   …` before, remove it. Otherwise every tool appears twice under two names.
3. **The plugin never publishes.** Every upload sets `publish: false`. You review the page in
   the Unbounce UI and publish there. It is your domain and your decision.

Changes to `.mcp.json` or `plugin.json` need `/reload-plugins` or a restart of Claude Code.

## Set up a folder for each brand

The plugin knows the platform. It does not know your brand, your domains, or your forms. That
knowledge lives in your own repository, in one folder for each brand.

1. Create a folder for the brand in your own working repository.
2. Copy `templates/client-setup/CLAUDE.md` from this plugin into that folder.
3. Give the copied file to Claude and ask it to complete what it can.
4. Answer the questions Claude asks. It cannot find some of the values on its own.

Claude finds these values itself:

- The domain and slug options, from `list_domains` on the account.
- The icon set and the brand-token source, from whatever `brand-extract` resolved.
- The correct tool-name prefix for the deny block, from `.mcp.json`.

Only you can answer these:

- Which form fields every page must carry, and which of them are required.
- The widget embed snippets, such as a review widget or a chat widget.
- The scripts the client wants at domain level, such as analytics or call tracking.
- The legal wording, footer, and any phone number that must appear.
- Who does the post-upload checklist in the editor.

Claude Code loads a root `CLAUDE.md` at the start of every session. So the completed file
works with no further setup. No skill has to read it.

One more block in that template needs no answers. It is a permissions deny list. Copy it into
the `.claude/settings.json` of your own repository and commit it. It blocks the two MCP tools
that flatten a native page. The plugin already escalates both calls to a human through a hook.
The deny list removes the judgement call in a repository that only holds native pages.

Multiple brands under one client get one folder each. Brands share nothing by default.

## Get the brand tokens in

Brand is an **input** to this plugin, never a part of it. No brand tokens, client assets, or
brand skills are tracked in this repository. The agent `agents/brand-extract.md` turns whatever
brand material you have into a token set that the design step uses directly.

These inputs work, best first:

| Input | Quality | How to give it |
|---|---|---|
| A design-system document (`DESIGN.md`, a tokens file, a Tailwind or CSS variables file) | Best. Exact values, no guessing. | Give Claude the path. |
| A design skill produced by **skillui** | Very good, with one caution below. | Give Claude the path to the generated folder. |
| A live website URL | Good. Claude reads the CSS custom properties and the computed styles. | Give Claude the URL. |
| A screenshot or a PDF | Approximate. Claude samples the colours by eye and says which values are estimates. | Give Claude the file. |

If you have several of these, give Claude all of them. Where they disagree, Claude reports the
disagreement instead of picking one in silence.

### Using skillui

[skillui](https://skillui.vercel.app/) is a separate command-line tool. It reads a website and
writes out its design system: colours, typography, spacing, animation, components, and
screenshots. The output is a folder that Claude Code reads. It is static analysis, so it needs
no API key and no cloud service.

Install it once:

```bash
npm install -g skillui
```

Extract a brand:

```bash
skillui --url https://www.example.com
```

For the full visual extraction, which adds scroll screenshots and animation detection, skillui
also needs Playwright:

```bash
npm install playwright
npx playwright install chromium
```

Then point Claude at the folder that skillui produced.

> **Caution.** The type tables that skillui extracts have been wrong in practice. It has
> swapped the body font and the heading font. Check every font assignment against one of the
> screenshots before you trust it. `brand-extract` is told to do this check, but a second pair
> of eyes costs nothing.

## Use it

The work splits into four skills. Each one starts where a working session naturally ends. Each
one reads its own `SKILL.md` and remembers nothing about the others. The files on disk are the
handover, so you can stop after any step and continue tomorrow or in a fresh session.

### 1. Design the page

Ask for the page. Claude reads the brand tokens, reads the geometry spec, and writes a design
HTML file straight to the Unbounce grid. It then measures the real text heights in a browser
and writes them back, and it repeats that loop until the numbers stop moving. A second agent
derives the mobile breakpoint and reports the decisions it made, such as *"hid the header phone
number, because the call-to-action covers it"*.

This step is a conversation. You steer the copy, the hierarchy, and the layout. Claude does not
stop and wait for approval in the middle of the loop. It builds something first, then shows you
screenshots and a design report you can react to.

You get a folder with two things in it: `design.html`, measured and stable, and a design
report. The report lists the decisions Claude made, the conversion choices and their
alternatives, and anything it left for the editor on purpose.

"Pick up the existing `design.html` and keep editing" is a normal way to start. It is not a
special case.

### 2. Build the file

```bash
python3 skills/build-page/scripts/transcribe.py design.html out.unbounce --page-name "My Page"
```

This step is mechanical. It reads the design file and writes the `.unbounce` archive. It uses
the Python standard library only, and it touches no network.

It also **refuses rather than repairs**. Geometry that sits off the grid or off the canvas is
an error in the design, and the transcriber reports it and writes nothing. That refusal is the
point. The moment the build step starts to correct the design, the design file stops being an
honest preview of the result.

Because it writes nothing on error, you can also use it as a free validator at design time.

### 3. Upload the file

This step needs the connected state. Claude uploads the file as an **unpublished** page, sets
the traffic mode, takes a full-page screenshot of the real render, walks that screenshot
against the design, and gives you a shareable preview link plus the page id.

Mobile is a manual check. The screenshot tool has no viewport setting, so Claude gives you a
preview URL to open at a 320px viewport. A real phone is better.

You publish, in the Unbounce UI, when you are happy.

### 4. Edit a live page

**This is not available yet.** The two tools it needs exist in the forked MCP, but nobody has
yet written an element array back to a live page and read it again to confirm what survived. A
write that appears to succeed and quietly damages the page is the worst failure this plugin can
produce, so the skill refuses to run.

Until that probe passes, change a live page by rebuilding it with steps 1 to 3 and uploading it
as a new page. The new page does not keep the old page id, URL, statistics, leads, or
integrations. Plan for that.

## What is in the repo

### The four skills

| Path | What it does |
|---|---|
| `skills/design-page/` | Brand, then layout, then the measure loop, then mobile, then sign-off. Produces a measured `design.html`. |
| `skills/build-page/` | Turns `design.html` into `out.unbounce`. Mechanical, standard library only, offline. |
| `skills/upload-page/` | Puts a `.unbounce` file into the account as an unpublished page, and verifies it. Needs the Unbounce MCP. |
| `skills/edit-page/` | Updates a live page in place. **Not available yet.** Read the file for what to do instead. |

### Scripts and agents

| Path | What it does |
|---|---|
| `skills/build-page/scripts/transcribe.py` | Design HTML to `.unbounce`. **Python standard library only.** |
| `skills/design-page/scripts/measure.mjs` | Real-browser text heights, image sizes, and overflow flags. |
| `skills/design-page/scripts/geometry.py` | Legal snap tables, nearest legal value, and measured-height write-back. |
| `agents/brand-extract.md` | Brand input (a URL, a `DESIGN.md`, a skillui folder, a screenshot, or a PDF) to tokens. |
| `agents/mobile-derive.md` | Desktop layout to mobile overrides, plus a report of the decisions. |
| `agents/build-pack.md` | Design HTML to a verified `.unbounce` archive. |
| `scripts/guard-native-page.py` | A `PreToolUse` hook. It stops the two MCP tools that flatten a native page. |

### Reference documents

These are the persistence layer. Every non-obvious platform fact in them was found by probing:
generate a varied page, upload it, download it again, and compare.

| Path | What it holds |
|---|---|
| `skills/design-page/references/design-rules.md` | The design contract, the form chrome, the mobile rules. |
| `skills/design-page/references/grid.md` | The geometry system, snap behaviour, what the validator enforces. |
| `skills/design-page/references/ui-capabilities.md` | Which features are safe to express, and which are not. |
| `skills/build-page/references/format.md` | The `.unbounce` file format itself. |
| `docs/adr/` | Settled architecture decisions and the reasons for them. |
| `templates/client-setup/CLAUDE.md` | The per-brand conventions template described above. |

## Platform limits you need to know

These come from Unbounce Classic, not from the plugin. You cannot design your way around them.

- **One form for each page.** This is a hard platform limit. Every other call-to-action on the
  page anchors down to that one form.
- **Classic Builder only.** A Smart Builder page cannot be exported or imported.
- **The mobile breakpoint is capped at 320px wide.** Design for it, do not fight it.
- **The page name inside the file wins** over the name given at upload. Set the name when you
  build the file.
- **A second page from the same design needs a new slug and a new name.** A collision with an
  existing page is the most common first failure at upload.

## What it deliberately does not do

- **No conversion-rate optimisation.** Message match, funnel design, heuristic scoring, and
  copy strategy belong to somebody else. This plugin does one thing: it produces Unbounce pages
  that need no repair.
- **No statistics, insights, or lead reporting.** The MCP can answer those questions directly,
  without this plugin.
- **No video elements and no lightboxes.** Neither has a verified shape inside the file. A
  lightbox flag set wrongly collapses the live mobile layout back to desktop, in silence. A
  video becomes an embed. A lightbox call-to-action becomes an anchor.
- **No `<select>` or `<textarea>` form fields.** Same reason. Add them natively in the editor
  after import. It takes about ten seconds.

The rule behind all four: a guess at an unproven shape produces a page that looks correct in
the editor and is broken on a real phone. That failure passes review, which makes it the worst
kind. The plugin refuses instead.

Two MCP tools break a native page, and the plugin guards both. `deploy_page` packs the whole
page body into one `lp-code` element, which is the exact failure this plugin exists to prevent.
`edit_variant` overwrites the first `lp-code` element it finds, which on these pages is a small
icon embed, so it destroys decoration and never touches the copy you meant to change. A hook
escalates both calls to you with the reason. Both tools are correct on a page that the MCP
manages as raw HTML, which is why the hook asks instead of refusing. On a page this plugin
built, the answer is no.

## Troubleshooting

**The upload step opens a browser and then times out.**
This is the interactive Unbounce login. Complete the login in the window that opened. The
server stores the session in `~/.unbounce-mcp/session.json` and later calls reuse it. The
upload itself often succeeds even when the login step reports a timeout, so check the account
before you retry.

**The screenshot step fails with a Chromium version error.**
The MCP carries its own Playwright, and it asks for a specific Chromium build. A plain `npx
playwright install chromium` fetches the build that your **local** Playwright maps to, which is
not necessarily the same one. Install the browser through the MCP's own Playwright command
line instead.

**Every MCP tool appears twice.**
You have the server installed twice, once by hand and once through the plugin. Remove the one
you added with `claude mcp add`.

**`set_traffic_mode` returns "Unauthorized" after an upload.**
Run the pending step again. **Do not upload the page again**, or you get two pages. With a
single variant at weight 100, all traffic goes there anyway, so the failure is usually
cosmetic. If the retry also fails, note it in the handover and move on.

**The design refuses to transcribe, with an off-grid or off-canvas error.**
The design is wrong, and this is working as intended. Fix the coordinates in `design.html`.
`skills/design-page/scripts/geometry.py` gives you the legal values to snap to.

**The page imports, but a section renders wrongly.**
Take this back to the design step. The build and upload steps do not repair pages.

**The client cannot drag a card as one unit.**
The card was built as flat, absolutely-positioned siblings instead of a box with its contents
nested inside it. A flat page passes every validator and still fails the client. Nesting is how
grouping works, and boxes nest to any depth.

**A change to `.mcp.json` or `plugin.json` has no effect.**
Run `/reload-plugins`, or restart Claude Code.

## Tests

```bash
python3 skills/build-page/scripts/test_transcribe.py
```

Run this after any change to the transcriber.
