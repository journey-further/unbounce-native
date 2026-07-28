# v2 — the connected plugin

Status: **agreed** (2026-07-28, Sam + Claude discussion), nothing implemented. v1
(`CLAUDE.md` → Status) is still unproven end-to-end; see Phase 3. Decisions D1–D8 are all
resolved inline; ADRs 0001 (MCP fork) and 0002 (skill split) record the two shape decisions.

## What v2 is

v1 can only ever **create**. It emits a `.unbounce` file, someone uploads it, and that is the
end of the relationship with the page. There is no import API that targets an existing page —
the upload path is the UI's importer, which always creates a new page and takes no page id.
So a page with live traffic cannot be updated without abandoning its stats, leads and form
integrations.

v2 adds a second state in which the plugin can **mutate** a page that already exists. The
divide is create-only vs mutate, not one-version vs variants.

| | Baseline | Connected |
|---|---|---|
| Credentials | none | API key + browser session |
| Design → build (steps 1–5) | identical | identical |
| Output | a `.unbounce` file | the same file |
| Upload | manual, via the UI | optional, automated |
| Read a live page back | ✗ | ✓ |
| Verify what the platform did on import | ✗ | ✓ |
| Update a page in place | ✗ | ✓ |
| A/B variants on a live page | ✗ | ✓ |

**Connected is the recommended state.** Baseline is the credential-free fallback, and its
real value is that it keeps the transcriber honest: stdlib-only, no network, air-gappable.
That property is what makes a baseline possible at all, so it is protected deliberately.

### Skill structure: four skills, files on disk as the contract

The single `design-page` skill splits along its natural session boundaries. Each skill's
input and output is a file in the working folder, so no skill needs another to be running —
or even to have run in the same session:

| Skill | In → out | Notes |
|---|---|---|
| `design-page` | brief → approved design HTML | Iterative, gated, **multi-session** — can pick up a previously designed page and keep editing. Ends at sign-off, not at build. |
| `build-page` | design HTML → `.unbounce` | Run-once, mechanical: measure, transcribe, validate. No creativity, no gates. |
| `upload-page` | `.unbounce` → page in the account | Run-once. Connected only. `publish: false`, screenshot both breakpoints, verify, hand back the preview URL. Never publishes — the client does that in the UI. |
| `edit-page` | live page + change request → same page, updated | Connected only. Fresh element read (never from cache — the client editing in the UI is the normal state of the world) → patch → write back in place → screenshot. Phase 4's variant flow bolts on here. |

### No branches, no configuration

No skill ever asks "am I connected?" — connected capability arrives as *whole skills*
(`upload-page`, `edit-page`) that simply do not function when the MCP tools are absent.
Baseline stops at `build-page`'s output: "here's your file, import it in the UI." A cold
session should never read `if connected do X else do Y` inside any skill's steps — that
doubles the decision surface at the step where models are weakest, and the bakeoff already
showed an arm working around a mechanic it half-understood.

Mode detection needs no configuration: skill availability follows tool availability. No
flag, no settings file, nothing to keep in sync.

## Requirements driving v2

Gathered from stakeholder requirements on a live engagement. Stated as capabilities so this
file stays client-neutral.

1. **Query-string values captured into the form.** A page must be able to read URL parameters
   into non-visible form fields so campaign attribution reaches the lead record. The
   script half is solved (domain-level script manager, or per-variant script slots); the
   field half is not expressible today.
2. **A brand-global modal/lightbox, triggered by class.** One promo dialog per brand, held in
   the account's global properties, fired by any button carrying an agreed class. Explicitly
   *not* per-page lightboxes — the stakeholder reached this conclusion independently, on the
   grounds that a promo change should not mean rebuilding every page.
3. **Standing per-client conventions.** A required tracking script, a mandatory hidden field,
   a specific review-widget embed, a chosen icon set. These are inputs, not plugin content —
   the same principle that already keeps brand out of this repo.
4. **Third-party widget embeds** as first-class inputs rather than placeholders.
5. **Multiple brands and domains** under one account, each with its own tokens and
   conventions.
6. **Variants of an existing page** for A/B testing, generated from a brief.

## Open decisions

Each has a recommendation. The recommendation is not the decision.

### D1 · External MCP, or a vendored subset? — **resolved: JF fork**

See ADR 0001. The MCP is consumed as a JF-maintained GitHub fork (legally clean — GitHub's
terms permit forking; vendoring unlicensed code into this repo is not ours to do). The fork
adds the D2 pair; the plugin manifest references the fork as its MCP server, so the client
still installs one thing. Vendoring proper stays a nice-to-have, unlocked only by a licence
grant (ask in the PR) or upstream abandonment.

### D2 · How does the plugin read and write native elements? — **resolved: fork the pair, PR upstream**

`get_variant` classifies our pages as Classic Builder and returns a rendered preview plus
modernization hints — not the element array. Both halves of the machinery exist upstream but
are unexposed: one internal function parses the array out of `edit.json`, another writes a
whole array back via `edit.json` + `save.xml`.

**Resolved: a `get_variant_elements` / `set_variant_elements` pair, added in the JF fork
now, PR'd upstream in parallel.** This is the keystone — verification, in-place update and
native variants all sit behind it, and it is small (~10 lines per tool; the machinery
exists). Why the pair and not the `.unbounce` export for reads: the only in-place *write*
mechanism takes an element array, so reading the same representation means read → patch →
write with no inverse-transcriber conversion step. Rule for the eventual skill steps: every
edit session starts with a fresh read — never patch from a cached array; the client editing
in the UI is the normal state of the world, not an edge case.

### D3 · Does the asset strategy change when connected?

Bundling and in-place update are **not** in tension. Images ride inside the `.unbounce` as
`assets/<uuid>/`; on import the platform takes ownership and rewrites the elements to its own
asset records. A later in-place edit reads those elements, patches copy or geometry, and writes
them back with image references untouched.

**Recommendation: keep bundling in both states.** Reach for asset upload only when an update
introduces a genuinely *new* image, in which case it is uploaded first and the element written
to the returned CDN URL. The build step never branches.

**Depends on P3** — the claim about what import does to asset references is reasoned, not
observed.

### D4 · Can baseline ship an A/B test at birth?

The archive format supports variants `a`–`z`; `transcribe.py` hardcodes one. Multi-variant
output would let baseline create a split test without any connected capability.

**Recommendation: defer.** It is a real capability with a hard ceiling — it can create a test
but never edit one, so it does not substitute for D2. Revisit only if the connected route
stalls.

### D5 · Where do stats, insights and leads live? — **resolved: not here**

This repo's product is designing to an Unbounce spec, then building/uploading the result.
Everything layered on top — stats, insights, leads, even additional design skills — is for
each client to decide as an enhancement in their own setup; none of it is a shippable
product of this repo. The split: page *construction and correctness* here, everything else
elsewhere. (The client has the MCP installed anyway, so stats/leads questions are already
answerable in their own Claude without this repo's involvement.)

### D6 · What shape does the per-client convention layer take? — **resolved: template**

Requirement 3's home is a per-brand working directory holding a `CLAUDE.md` of standing
instructions, brand tokens, required scripts and widget embeds — one per brand, since
requirement 5 is multi-brand.

**Resolved:** ship a starter template in the repo (`templates/client-setup/CLAUDE.md`,
client-neutral, commented slots for tokens / domain scripts / mandatory hidden fields /
widget embeds). The template *is* the documentation. No validator — revisit only if a
convention file causes a real mess in practice.

### D7 · Sandbox account — **resolved: not needed yet**

The client account has no live traffic to damage: one listed domain, not actually connected
to DNS. The working norm (client-agreed) is that the MCP never publishes — pages are uploaded
`publish: false` and the client checks and publishes in the UI. Mutate probes therefore run
against throwaway pages in the client account, deleted afterwards.

**Ceiling:** the moment a domain is genuinely connected and a page carries traffic, mutate
probes must stop targeting the live account and this decision gets revisited (dummy
sub-account or a never-completed domain setup are both cheap options then).

### D8 · Does the two-state model belong in `CLAUDE.md`? — **resolved: yes**

It shapes what may enter the repo, which makes it a standing constraint rather than a task.
D1 and D5 are settled, so the section can be written: the two states, the external-MCP
decision (ADR 0001), and the D5 scope line. Written as part of executing this plan.

## Probes required

Doctrine: unproven means refuse. Emitting a guess produces a page that looks right in the
editor and is broken live — the worst failure, because it passes review.

### P1 · Hidden form field shape — **highest priority**

`INPUT_LPTYPE` (`transcribe.py:32-36`) covers `text`, `email` and `tel`. Nothing else;
`select` and `textarea` are refused outright at `transcribe.py:120`. A non-visible field has
no verified shape.

**Method:** add one in the editor, export the `.unbounce`, read the JSON. Needs no connected
capability — it can be done today.
**Blocks:** requirement 1 entirely. The tracking script has nothing to write into until this
lands.
**Watch for:** whether the field participates in the 80px field stride and the label budget,
or sits outside the laid-out stack.

### P2 · Does a class-triggered global lightbox fire on a page built with `hasLightbox: false`?

Requirement 2's mechanism lives in account globals, not in the page. Our pages set
`hasLightbox: false` deliberately: `true` without a proper lightbox sub-page tree makes the
**live** renderer collapse the page to desktop layout on mobile while the editor looks fine.

**Method:** build a page with a button carrying the agreed class, define the global dialog,
publish, test on a real device.
**Blocks:** confirming requirement 2. The class-emission half already works —
`customClassnames` (`transcribe.py:246-256`) is the editor's own custom-class field.
**If it needs the flag set:** requirement 2 becomes genuinely expensive and the honest answer
is that the dialog is added in the editor.

### P3 · What does import do to asset references?

**Method:** the round-trip — upload, read the elements back, diff against what was emitted.
**Blocks:** D3.
**Note:** needs D2, or a manual export in the meantime.

### P4 · Does a written element array survive?

Writing a whole element array back is the mechanism behind in-place update and variants.
Unverified end to end: whether the editor preserves it across a save, and whether geometry,
custom classes and asset references all survive.

**Method:** read, change one string, write, re-read, diff. Then open the page in the editor,
save, and diff again.
**Blocks:** every mutate capability.

### P5 · Icon-set integration

Only Google Fonts are wired into the font path (`transcribe.py:114`, `:208`). An icon font
from another CDN is not. The SVG route works today — icons already ship as small `lp-code`
elements — so the likely answer is "yes as SVG, no as a font".

**Method:** confirm the SVG route renders live; check whether `webFontsExternalInUse`
(currently always empty) is the hook for an external font, or vestigial.
**Blocks:** nothing. Answer it to close the question honestly.

### P6 · Multi-variant archive shape

Only if D4 is revived. Probe the archive layout for variants `b`+ before emitting one.

## Sequencing

**Phase 1 — probes + skill changes, one piece.** P1, P2, P5, the skill changes they drive,
and the four-skill split (`design-page` → `design-page` / `build-page` / `upload-page` /
`edit-page` skeletons), worked as a single batch so the findings go back to the stakeholder
together — in case any of them (P2 especially) changes the shape of what was promised.
Handover deliberately waits for this batch: shipping today's version isn't worth it when the
v2 cut is close. Only `upload-page`/`edit-page` content needs connected work; the split
itself and the probes do not, and two of the probes are commitments already made.

**Phase 2 — connected core.** Promoted from follow-up to fundamental: the realistic client
workflow is iterative (upload → stakeholder feedback → Claude edits → push back to the *same*
page), and Claude must never work off stale code, so the mutate loop is part of the handover
cut, not an update that arrives later. Fork the MCP, add the D2 pair, open the upstream PR →
P4 immediately (it is the kill-shot: if a written array does not survive an editor save, the
loop is dead regardless of tooling and handover reverts to create-only) → P3 → the mutate
loop as documented skill steps. Runs against throwaway pages per D7.

**Phase 3 — prove it, then hand over.** Merge `dev` → `main` first: the public repo's `main`
predates the bakeoff fixes and the skill rename, so an install before the merge gets the
wrong version and a skill name that does not match what was demonstrated. Then the
cold-start acceptance run, executed by us before handover: fresh context, no memory, design
brief + brand tokens only — ideally a real brief requested from the client. The bakeoff does
not count; it ran unaided with no design gates, so the gated interactive flow is untested in
a fresh window. Handover follows the run and is explicitly not gated on perfection — the
client testing it and feeding back is part of the plan, with support expected. Unchanged
definition of done: imports, renders correctly **live** on mobile, images correct, a whole
card drags as one unit — plus the mutate loop demonstrated once end to end.

**Phase 4 — variants.** Requirement 6, on top of Phase 2's pair. Cheap once the keystone
exists (`duplicate_variant` → patch elements → `rename_variant` → `set_variant_weights`),
but not handover-blocking.

## Definition of done for v2

- Baseline still works with no credentials and no network beyond design-time measurement.
- A page built by the plugin can be updated in place without losing its id, URL, stats, leads
  or integrations.
- The round-trip probe runs as a command, not a manual browser session.
- Requirements 1 and 2 are either supported or explicitly refused in the handover, with the
  reason.
- No skill contains a connected/baseline branch; connected capability exists only as the
  `upload-page` and `edit-page` skills.
- A design can be resumed and edited across sessions, and `build-page` runs from a design it
  did not create in-session.
- Nothing client-specific or brand-specific has entered a tracked path.
