# The `.unbounce` file format

Everything here is verified against two real Classic Builder exports and confirmed by a
real upload that imported, rendered and served mobile correctly. Where something is
unproven it says so — **unproven means "don't emit it", not "guess it"**.

## TL;DR

A `.unbounce` file is a **GNU tar** (not a zip, despite the common `.zip` rename trick) of
JSON plus image assets. `elements.json` is a flat array of `lp-pom-*` elements, each with
absolute geometry and a `breakpoints.mobile` override. Text is inline-styled HTML, so
**arbitrary hex colours and any Google Font are expressible in the file even though the
editor's own pickers can't set them.** That is the whole reason generating the file beats
clicking in the UI — and the elements stay native, so the client can still edit them.

## Archive layout

```
<archive-id>/                            # 16 hex chars, any value
  assets/<uuid>/<filename>               # one dir per image asset
  pages/<page-id>/
    source.json                          # {"source_uuid": "<uuid>"}
    metadata.json                        # {"name": "...", "champion_variant_id": "a"}
    page_variants/a/
      metadata.json                      # variant name, last_element_id, has_form, version "4.2", template_id
      settings.json                      # builder settings, fonts, goals, breakpoint flags
      elements.json                      # THE PAGE — flat array
      styles.json                        # empty file (0 bytes) on a real export
      javascripts.json                   # empty file (0 bytes)
      keywords.json                      # empty file (0 bytes)
      attachments.json                   # {"uuids": []}
      sub_pages/<id>/                     # same structure recursively
```

Pack as **GNU tar** with the `<archive-id>/` dir at top level, members owned
`nobody/nogroup`, uid/gid 0, directory entries included, no `.DS_Store`.

`version: "4.2"`, `builderVersion: "v6.24.319"`, and `template_id: 0` (or `null`) are all
accepted — there is no template registry check.

### Sub-pages

`metadata.json` carries `used_as`, and the sub-variant's `settings.json` carries a
`mainPage: {uuid, variant_id}` back-reference to the parent's `source_uuid`.

- `used_as: "form_confirmation"`, `path_name: "a-form_confirmation.html"` — **required** if
  the page has a form with `confirmAction: "modal"`.
- `used_as: "lightbox"` — **we never ship one.** See the `hasLightbox` warning below.

## `elements.json`

Flat array; the tree is expressed purely via `containerId`. IDs are
`lp-pom-<type>-<n>` with `<n>` a single integer sequence shared across all types; the
maximum is recorded as `last_element_id` in the variant `metadata.json`.

**The nine primitives we emit** — exactly the set a real 92-element page used, no more:

| Type | Role |
|---|---|
| `lp-pom-root` | the page; `contentWidth` per breakpoint |
| `lp-pom-block` | a section — full-width band, stacks vertically, `fitWidthToPage: true` |
| `lp-pom-box` | a rectangle: cards, overlays, dividers, accent strips, badges |
| `lp-pom-text` | inline-styled HTML in `content.text` |
| `lp-pom-image` | references an `assets/<uuid>/` file |
| `lp-pom-button` | full up/hover/active styling, `action.type` url/form/tel |
| `lp-pom-form` | the one form; submit button is a **separate child element** |
| `lp-code` | Custom HTML (embeds, SVG flourishes, third-party widgets) |
| `lp-stylesheet` | page-wide CSS, `containerId: null`, `placement: "body:after"` |

`lp-pom-video` and lightbox buttons/sub-pages are **excluded**: video appears in no real
export (untested path) and the lightbox is an active landmine (see `hasLightbox`). A video
becomes an `lp-code` embed; a lightbox CTA becomes an anchor or a second page.
`lp-script` exists (same shape as `lp-stylesheet`, `placement: "head"|"body:before"|"body:after"`)
but nothing we generate needs it.

**`customClassnames`** — a top-level string key on any element, sibling of `breakpoints`,
absent unless set. It is the editor's own "custom class" field, so it round-trips safely.
Proven by setting a class in the editor on an `lp-pom-box` and re-downloading:
`"customClassnames": "test_class"`. This is the supported way to give the stylesheet a
shared hook instead of a list of ids, and the client can add or remove the class from the
UI. Space-separating multiple classes is the obvious reading of the plural name but is
**not yet proven** — probe before emitting more than one.

⚠️ **A string, never an array.** `customClassnames: ["x"]` is accepted by the save API
without complaint and then blanks the entire page — blank at both breakpoints and "Unable to
load your page" in the editor (the P4 failure, root-caused 2026-07-29). The same value as a
plain string renders perfectly. Wrong-typed field values generally are the page-destroying
class of mistake: Unbounce stores them and dies at render, so nothing catches them before a
screenshot does.

### Layout model

- Blocks are `position: relative` and stack in array order. Children are
  `position: absolute` with `offset {left, top}` + `size {width, height}` **relative to
  their container**, not to the page.
- Every element carries `breakpoints.mobile` with override geometry (`visible`, `offset`,
  `size`, `scale`). Desktop and mobile are **two hand-positioned layouts of one shared
  element tree** — Classic does not reflow. `visible: false` hides an element at that
  breakpoint.
- Blocks also carry `grid` (columns/rowHeight/xGap/yGap/padding/snapToGrid). This is
  **editor chrome only** — an off-grid element renders off-grid in preview regardless.
  See `grid.md`.
- **Nesting is grouping.** Dragging an element into a box in the editor is nothing but
  `containerId` + offsets relative to the new parent — no flags, no extra fields
  (verified field-by-field against a hand-grouped export). "Center to bounding box" just
  computes `(box_w − child_w)/2` and stores an ordinary offset. This is why the DOM tree
  of the design HTML can *be* the `containerId` tree.
  **⚠️ Rebase both breakpoints consistently.** The editor re-parents only the breakpoint
  you are editing, so a hand-grouped page can end up with correct mobile offsets and
  double-counted desktop ones (an element at desktop x=1588 on a 1440 canvas). Generated
  files must never reproduce that.

### Styling — the editor's limits do not apply

- **Text:** `content.text` is raw HTML with inline styles — any `font-family`,
  `font-size`, `color`, `line-height` per span. `content.fonts` lists families used.
- **Buttons:** `up`/`hover`/`active` states each take arbitrary hex `backgroundColor` /
  `color` / gradient, plus `cornerRadius`, `fontFamily`, `letterSpacing`, `textTransform`.
  **No border** — `{"style": "none"}` is hardcoded in the `up` state, so an outline button
  is not expressible.
- **Backgrounds:** solid hex only — every emitter writes `newBackground.type:
  "solidColor"`. A gradient in the design flattens to a composite wash; the real gradient
  JSON shape is unproven, so probe (upload → download → diff) before ever emitting one.
- **Fonts:** register in `settings.json` → `fonts[]`
  (`{family, variants:[{name, fontWeight, fontStyle, displayName}]}`) **and**
  `webFontsInUse: {family: [weights]}`, then use the family in inline styles. No picker
  involved. Confirmed rendering for Google Fonts declared this way.
- **Fonts from outside Google need no registration at all.** Proven 2026-07-29 (P5): a
  stylesheet `<link>` inside an `lp-code` element loads live and its CSS is document-global, so
  a `font-family` in `content.text` renders even though the family is in neither `fonts[]` nor
  `webFontsInUse`. `content.fonts` stays `[]` and that is fine. Recipe and the CSS-quoting trap
  are in `skills/design-page/references/ui-capabilities.md` → *External fonts*.
- **`webFontsExternalInUse` stays `{}`.** It records fonts registered through the editor's
  Settings → Add custom fonts, not anything we emit; its in-file shape is unproven. Both real
  exports carry `{}`, including the one using two Google families. Do not populate it.

### Images — native images STRETCH

There is **no native block background-image** to lean on; real exports use solid-colour
blocks plus a full-bleed `lp-pom-image` for every background. And an `lp-pom-image` scales
to its box with no cover/contain. So:

- **Backgrounds & cropped photos:** size the element to the crop frame, `maintainAR: false`,
  and add an `lp-stylesheet` rule
  `#lp-pom-image-<id> img{width:100%!important;height:100%!important;object-fit:cover!important}`.
- **Logos & content images:** aspect-ratio-correct dimensions, `maintainAR: true`,
  `object-fit: contain`. **Never size a small image up to full width** — it stretches tall.
- **No alpha.** `lp-pom-image` has no opacity channel; `background.opacity` on an image is
  the fallback fill, not the image. A washed photo is a solid wash on the block, not a
  translucent image.

Asset record shape (mirror it exactly — this is what makes ingestion work):

```json
{"company_id": 0, "uuid": "<uuid>", "name": "roof.webp",
 "unique_url": "/assets/<uuid>/<8hex>-roof.webp",
 "content_url": "/assets/<uuid>/roof.original.webp?1779210799",
 "content_content_type": "image/webp", "content_file_size": 123456,
 "size": {"width": 2189, "height": 1642}, "sizeVerified": true}
```

`size` must be the **real natural pixel size** — the transcriber cannot read image headers
(stdlib can't parse webp), so `measure.mjs` reports `naturalWidth`/`naturalHeight` and the
design HTML carries them as `data-nat="WxH"`. webp and png both ingest fine. Asset
ingestion runs ImageMagick server-side, so odd synthetic PNGs can be rejected; real photos
are fine.

### Forms

**One form per page — a Classic hard limit.** Additional CTAs anchor back to it
(`action: {type: "url", url: "#lp-pom-form-<n>"}`).

- `content.fields[]`: `{name, id, placeholder, type: "text", lpType, show: {phone, email},
  validations: {required, email, phone}, uuid}`, plus `validationType: "north-american"` on
  phone fields.
- `content.steps[]`: `[{uuid, fieldUUIDs: [...]}]` — field ordering.
- **Proven `lpType` values only:** `single-line-text` (optionally with
  `validations.email` / `validations.phone`) and `hidden`. `<select>` and `<textarea>` appear
  in no real export, so their in-file shape is unknown — the transcriber rejects them and
  tells you to add the field natively in the editor.
- **Hidden fields** (proven 2026-07-28, purpose-built export from the Classic editor — the
  editor's field-type dropdown offers "Hidden Field"). A *different* field shape, not a
  variant of the visible one:

  ```json
  {"name": "utm_source", "id": "utm_source", "type": "hidden", "lpType": "hidden",
   "value": "ppc", "uuid": "…"}
  ```

  - `type` is `"hidden"`, not `"text"`. There is **no `placeholder`, no `show`, no
    `validations`** — a `value` instead, which is the field's default/prefilled content.
  - It **does** appear in `content.steps[].fieldUUIDs`, so it submits like any other field.
  - **It is laid out outside the visible field stride.** Its only `publishedStyles` entry is
    a bare `#<id>` at `{top: 0, left: 0, width: 0, height: 0}` — no `#container_`, no input
    item, no `#label_`. It is appended **after** all visible entries, in both the desktop and
    mobile arrays. So it consumes no vertical space and the form's height budget counts
    visible fields only.
  - Evidence limit: the probed export had the hidden field **last**. A hidden field in the
    middle of the list is untested — the transcriber therefore indexes the stride by visible
    fields only and appends hidden entries, which reproduces the proven file exactly. If a
    design ever needs one mid-list, re-probe rather than trusting the generalisation.
  - Populating it from a URL parameter is a **domain-level script**, not a page-level one —
    a client-setup convention (`templates/client-setup/CLAUDE.md`), not plugin content.
    Unbounce's native Dynamic Text Replacement is a different mechanism: it personalises page
    *copy* from URL params and does **not** write to the lead record.
- The submit button is a **separate `lp-pom-button` whose `containerId` is the form**,
  referenced by `content.buttonId`. Because it is a form child, any block-level layout
  pass misses it — size it explicitly at both breakpoints or it clips.
- **`publishedStyles` is a TOP-LEVEL array on the form element**, not under `content`
  (a check that looked under `content` wrongly reported it null). 3 entries per field —
  `#container_<id>`, the input item, `#label_<id>`. Real exports carry width 468 (desktop)
  and 240 (mobile).
- **⚠️ `publishedStyles` is DERIVED, not authored — the editor recomputes it on save.**
  Confirmed by round-trip diff: a page uploaded with the 53/71/34/19/15 numbers copied from
  a real export came back 62/80/46/16/12 after one editor save, because our form chrome is
  taller than that export's. Hard-coded numbers publish a field stack that doesn't match the
  inputs' real heights — fields overlap on a page published without ever opening the editor.
  The formula, fitted to both observations:

  ```
  label height    = round(label font size * 1.1)      # 11 -> 12, 14 -> 15
  input height    = geometry.field.height + 2 * border width
  input top       = label height + label margin.bottom
  container height= input top + input height
  stride          = container height + field margin.bottom
  ```

  The transcriber derives all five from the chrome constants in `form()`. Change the chrome
  and the stride follows; the design-time CSS in `design-rules.md` mirrors the same numbers.
- `computations.labelHeight` on buttons is likewise recomputed from the real font metrics
  (19 → 14/17 on save). Harmless — it's a cache, not layout input.
- **⚠️ Desktop and mobile `publishedStyles` must be independent copies.** Sharing one list
  object between breakpoints silently halved the desktop field widths when the mobile
  widths were rewritten.

### Custom HTML (`lp-code`)

`content.html` = the raw snippet, positioned like any other element. Third-party review
widgets and embed scripts live here.

**⚠️ Never put the literal string `<head>` in any `lp-code` / `lp-stylesheet` content.** The
publisher literal-replaces every occurrence anywhere in page content — even inside script
bodies and JSON strings — with an injected meta tag, corrupting it.

### Stylesheets (`lp-stylesheet`)

`containerId: null`, `placement: "body:after"`, `content.html` = `<style>…</style>`.

**Every rule targets a `customClassnames` class, never an element id** — see the hard rule
in `SKILL.md`. `object-fit` ships as `.fit-cover img{…}` / `.fit-contain img{…}`, one rule
however many images, and the client can move an image between them from the editor.

**Carry mechanics only** — image `object-fit`, form-field `:focus` ring, link reset.
Everything content- and brand-related stays **inline** so the client can edit copy, colour
and font in the native editor. Rule of thumb: persistent CSS is behaviour the client
shouldn't touch; inline is what they will. Brand tokens in the sheet create a second
source of truth the editor can't reach.

## `settings.json` — the three flags that decide whether mobile works

```json
{"defaultWidth": 760, "builderVersion": "v6.24.319", "contentType": "pageVariant",
 "activeGoals": [{"type": "form", "url": "/fs", "sortOrder": 1}],
 "fonts": [...], "webFontsInUse": {...},
 "multipleBreakpointsEnabled": true, "hasLightbox": false,
 "tabletBreakpointDisabled": true, "multipleBreakpointsVisibility": true,
 "globalImageQuality": {"value": 60, "compressPng": true}, "refId": 1}
```

Three render-breakers, each found by diffing a save-repaired export against a generated
one. All three present as "looks fine in the editor, wrong on a real phone":

1. **`multipleBreakpointsEnabled` must be `true`.** Both real exports ship it `false`. With
   it false the mobile geometry still exists and the *editor* shows it when you toggle
   breakpoints, but **preview and live serve the DESKTOP layout to phones**. Set it on
   **every** `settings.json` in the archive, including sub-pages.
2. **`hasLightbox` must be `false` if there is no lightbox sub-page.** The blank template
   ships it `true`. Left true with no lightbox data, the **live** renderer hunts for the
   missing data and drops the whole page to the desktop layout on mobile. The editor is
   tolerant, so this is the "works in preview, broken live until I open and save" symptom.
3. **Every `scale` must be a NUMBER — never the string `"fit"`.** The editor tolerates
   `scale: "fit"`; the live/preview renderer rejects it and **drops the entire page's
   mobile layout to desktop**. On save Unbounce converts visible `"fit"` values to a
   computed numeric scale and leaves hidden ones alone. Emit numbers only.

## Upload

- **Download/upload is Classic Builder only.** Smart Builder pages cannot be exported or
  imported at all.
- All Pages → "Upload an Unbounce Page" → one file at a time, processed async, email
  confirms. There is no public import API.
- Uploaded pages arrive **unpublished**, stats zeroed, and often in **"weighted" (A/B)
  routing mode even as a single variant** — reset traffic mode after import.
- Preview a variant without burning stats by appending the variant letter + `.html` to the
  published URL (`…/my-page/a.html`).
- Element `type`/`id` map 1:1 to published DOM ids and classes, so anchors and custom CSS
  can target them reliably.
- Cross-account moves: a sub-account copy loses stats; fully separate accounts need
  Unbounce Support.

## The probe-then-diff pattern

Every non-obvious fact above was found the same way, and it is the definitive way to
answer the next format question:

1. Generate a deliberately varied page (e.g. six sections each with a different grid
   config) and upload it.
2. Inspect in the editor / on a real device, then **download it again**.
3. Diff the downloaded JSON against what you uploaded. What Unbounce silently changed is
   the answer.

`scale: "fit"`, `hasLightbox`, `multipleBreakpointsEnabled` and the shared-`publishedStyles`
bug were all found this way. Do this before writing an emitter for anything unproven.
