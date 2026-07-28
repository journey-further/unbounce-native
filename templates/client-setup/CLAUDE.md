# <Client name> — Unbounce page conventions

<!--
  TEMPLATE. Copy this file into the client's own working repo, one folder per brand, and fill
  in the slots. It is not filled in here: this plugin repo is client-shippable and nothing
  brand-specific or client-specific may be tracked in it.

  What this file is for: the standing conventions every page for this brand must follow.
  The plugin knows the platform; this file knows the client. Delete any slot that doesn't
  apply — an empty slot with a comment is better than a guessed value, but a slot you know
  is irrelevant is just noise.

  Multiple brands under one client = one folder each, each with its own copy of this file.
  Brands share nothing by default; a shared value that really is shared gets duplicated, not
  abstracted into a parent.
-->

## Brand tokens

<!--
  Where the design step gets colours, fonts, radii and spacing. Point at the source, don't
  transcribe it here — a copied token set goes stale silently.

  A path to a design-system doc or tokens file is best (exact values, no inference). A URL,
  screenshot or PDF also works; `brand-extract` handles all of them.
-->

- Source:
- Anything `brand-extract` gets wrong and has to be told:

## Domains

<!--
  Which domain each kind of page publishes on, and the slug convention. `list_domains` gives
  the options the account actually has. Note that the plugin never publishes — this tells
  the upload step which domain to configure, and tells the client where to expect the page.
-->

- Primary domain:
- Slug convention:

## Mandatory form fields

<!--
  Fields every page's form must carry, and which are required. One form per page is a
  platform hard limit, so this list is the whole form contract.

  Only `text`, `email`, `tel` and `hidden` have a proven in-file shape. `<select>` and
  `<textarea>` are added in the editor after import — if this brand needs one on every page,
  say so here so it lands in the post-upload checklist rather than being forgotten.

  Hidden fields take no vertical space and submit into the lead record, so this is where to
  list the tracking fields every form must carry (utm_source, gclid, a campaign id…).
-->

| Field | Type | Required | Notes |
|---|---|---|---|
|  |  |  |  |

## Domain-level scripts

<!--
  JavaScript the client wants on every page, added at the account/domain level in Unbounce
  rather than baked into each page file. Paste the actual snippet, not a description of it.

  Typical: analytics, call tracking, a URL-parameter capture script.

  The URL-param → hidden-field pattern lives here. The page file provides the hidden field
  (list it under mandatory fields above); the script that reads `location.search` and fills it
  is domain-level, because it's the same script on every page and the client can change it
  without a rebuild. Name the field the script targets so the two stay in sync.
-->

## Widget embeds

<!--
  Third-party embeds — review widgets, chat, booking. The client's own snippet, pasted
  verbatim, plus where on the page it goes and how much vertical space to reserve.

  Each one ships as its own small `lp-code` element. That is the sanctioned use. A
  page-shaped `lp-code` is the failure the plugin exists to avoid.
-->

| Widget | Placement | Reserved size | Snippet |
|---|---|---|---|
|  |  |  |  |

## Icons

<!--
  Which icon set this brand uses, and where the files come from. Inline SVG in a small
  `lp-code` element is the proven route and renders correctly live (confirmed 2026-07-28). An
  icon *font* served from a non-Google CDN is unproven — use SVG.
-->

- Set:
- Source:

## Anything else on every page

<!--
  Legal disclaimer wording, a required footer, a cookie notice, an accessibility statement,
  a phone number that must appear in the header. Anything the client will notice is missing.
-->

## Post-upload checklist for this brand

<!--
  The client-specific half of the handover. The plugin already covers the platform half
  (reset traffic mode, check a real phone). This is what *this* brand needs someone to do in
  the editor after import — and who does it.
-->

- [ ]
