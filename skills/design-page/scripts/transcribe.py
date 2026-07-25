#!/usr/bin/env python3
"""Transcribe an annotated design HTML file into a native .unbounce archive.

Mechanical transcription, NOT transformation: every positioned element in the design
maps 1:1 to one lp-pom-* element at the same geometry. The transcriber never moves
anything — if geometry is off-grid or off-canvas it errors and the design gets fixed.

    python3 transcribe.py design.html out.unbounce --page-name "My Page"

Stdlib only (no pip, no network). Run scripts/measure.mjs first: it supplies the
measured text heights and image `data-nat` dimensions this script consumes.

See references/format.md (file format), references/grid.md (geometry + snap),
references/design-rules.md (the design contract this parses).
"""
import argparse, json, os, re, shutil, sys, tarfile, uuid
from html.parser import HTMLParser

# ---- geometry system: references/grid.md ----
BP = {
    "desktop": dict(canvas=1280, pad=70, cols=24, colw=36, pitch=48, rh=12),
    "mobile":  dict(canvas=320,  pad=10, cols=6,  colw=40, pitch=52, rh=12),
}
MEDIA_PROPS = {"left", "top", "width", "height", "display"}
LP_TYPES = {"block": "lp-pom-block", "box": "lp-pom-box", "text": "lp-pom-text",
            "image": "lp-pom-image", "button": "lp-pom-button", "form": "lp-pom-form",
            "code": "lp-code", "submit": "lp-pom-button"}
VOID = {"img", "input", "br", "hr", "meta", "link", "source", "col"}
# custom classes end up in a stylesheet selector, so they must be plain CSS identifiers
CLASS_RE = re.compile(r"-?[A-Za-z_][A-Za-z0-9_-]*")
# lpType values proven in real exports. Anything else is an error, never a guess.
INPUT_LPTYPE = {
    "text":  ("single-line-text", {}),
    "email": ("single-line-text", {"email": True}),
    "tel":   ("single-line-text", {"phone": True}),
}


# ---------------------------------------------------------------- parsing
def decls(s):
    out = {}
    for d in (s or "").split(";"):
        if ":" in d:
            k, v = d.split(":", 1)
            # the mobile block requires !important on every declaration (an inline style
            # attribute outranks a media query otherwise) — it carries no meaning here
            out[k.strip().lower()] = re.sub(r"\s*!\s*important\s*$", "", v.strip(), flags=re.I)
    return out


def px(v, default=None):
    m = re.match(r"^-?[\d.]+", str(v or ""))
    return float(m.group()) if m else default


def hexcolor(v, default=None):
    """First colour token anywhere in the value — shorthand like `1px solid #e8e8e8` or
    `url(…) #fff` must not fall through to the default. rgba alpha is discarded (the
    format has nowhere to put it — design-rules.md's Opacity section)."""
    if not v:
        return default
    m = re.search(r"#([0-9a-fA-F]{6})\b|#([0-9a-fA-F]{3})\b|rgba?\(\s*(\d+)\D+(\d+)\D+(\d+)",
                  str(v))
    if not m:
        return default
    if m.group(1):
        return m.group(1).lower()
    if m.group(2):
        return "".join(c * 2 for c in m.group(2))
    return "%02x%02x%02x" % tuple(int(g) for g in m.group(3, 4, 5))


def label_text(inner):
    """Button label from captured inner HTML: tags stripped, whitespace collapsed."""
    from html import unescape
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(inner))).strip()


def darken(hx, f=0.88):
    r, g, b = (int(hx[i:i + 2], 16) for i in (0, 2, 4))
    return "%02x%02x%02x" % tuple(max(0, min(255, int(c * f))) for c in (r, g, b))


class Design(HTMLParser):
    """Reads the design contract: data-lp-type + inline geometry + one @media block."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.nodes, self.open, self.css = [], [], []
        self.cap = None            # (node, tag, depth) — raw innerHTML capture
        self.in_style = False
        self.body = {}
        self.font_href = None
        self.errors = []

    # -- raw capture ------------------------------------------------
    def _raw(self, s):
        if self.cap:
            self.cap[0]["inner"].append(s)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs, self_closing=True)

    def handle_starttag(self, tag, attrs, self_closing=False):
        a = {k.lower(): (v or "") for k, v in attrs}
        if self.cap:
            self._raw(self.get_starttag_text())
            if tag == self.cap[1] and tag not in VOID and not self_closing:
                self.cap[2].append(1)
            return
        if tag == "style":
            self.in_style = True
            return
        if tag == "link" and "fonts.googleapis.com" in a.get("href", ""):
            self.font_href = a["href"]
            return
        if tag == "body":
            self.body = a
            return
        if tag in ("select", "textarea"):
            self.errors.append(f"<{tag}> has no verified in-file shape — "
                               "remove it and add the field natively in the Unbounce editor")
            return
        parent = self.open[-1] if self.open else None
        lp = a.get("data-lp-type")
        if tag == "input" and parent and parent["lp"] == "form":
            parent["fields"].append(a)
            return
        if not lp:
            return
        if lp not in LP_TYPES:
            self.errors.append(f"unknown data-lp-type={lp!r} on #{a.get('id')}")
            return
        n = dict(lp=lp, tag=tag, attrs=a, id=a.get("id"), style=decls(a.get("style")),
                 parent=parent, inner=[], fields=[], kids=[])
        if not n["id"]:
            self.errors.append(f"every data-lp-type element needs an id ({lp} in "
                               f"#{parent['id'] if parent else 'body'})")
            n["id"] = f"__anon-{len(self.nodes)}"
        self.nodes.append(n)
        if parent:
            parent["kids"].append(n)
        if tag in VOID or self_closing:
            return
        self.open.append(n)
        # buttons capture too: their inner text is the label (design-rules.md)
        if lp in ("text", "code", "button", "submit"):
            self.cap = (n, tag, [1])

    def handle_endtag(self, tag):
        if self.cap:
            if tag == self.cap[1]:
                self.cap[2].pop()
                if not self.cap[2]:
                    self.open.pop()
                    self.cap = None
                    return
            self._raw(f"</{tag}>")
            return
        if tag == "style":
            self.in_style = False
        elif self.open and self.open[-1]["tag"] == tag:
            self.open.pop()

    def handle_data(self, d):
        if self.cap:
            self._raw(d)
        elif self.in_style:
            self.css.append(d)

    def handle_entityref(self, n):
        self._raw(f"&{n};")

    def handle_charref(self, n):
        self._raw(f"&#{n};")

    def handle_comment(self, d):
        self._raw(f"<!--{d}-->")


def media_rules(css, errors):
    """Parse the pinned-grammar mobile block: @media (max-width:600px){ #id{...} }."""
    i = css.find("@media")
    if i < 0:
        return {}
    j = css.index("{", i)
    depth, body = 0, ""
    for k in range(j, len(css)):
        if css[k] == "{":
            depth += 1
        elif css[k] == "}":
            depth -= 1
            if depth == 0:
                body = css[j + 1:k]
                break
    rules = {}
    for m in re.finditer(r"#([\w-]+)\s*\{([^}]*)\}", body):
        d = decls(m.group(2))
        for prop in d:
            if prop not in MEDIA_PROPS:
                errors.append(f"#{m.group(1)}: '{prop}' is not allowed in the mobile block "
                              f"(whitelist: {', '.join(sorted(MEDIA_PROPS))})")
        rules[m.group(1)] = d
    return rules


def parse_fonts(href):
    """Google Fonts link -> (settings fonts[], webFontsInUse{})."""
    fonts, in_use = [], {}
    for fam in re.findall(r"family=([^&]+)", href or ""):
        name, _, spec = fam.partition(":")
        name = name.replace("+", " ")
        weights = sorted({w for w in re.findall(r"\b([1-9]00)\b", spec)}) or ["400"]
        in_use[name] = weights
        fonts.append({"family": name, "variants": [
            {"name": "regular" if w == "400" else w, "fontWeight": int(w),
             "fontStyle": "normal",
             "displayName": f"{name} {w}"} for w in weights]})
    return fonts, in_use


# ---------------------------------------------------------------- emitters
# Lifted from the proven build_ridgeline_unbounce.py emitters (shapes verified against
# two real exports + a real upload) and parameterised — every constant is now an input.
class Build:
    def __init__(self):
        self.n = 10
        self.els = []
        self.fit = set()              # "cover" / "contain" — which fit classes are in use
        self.classes = {}             # lp id -> [class names]

    def nid(self, kind):
        self.n += 1
        return f"lp-{kind}-{self.n}"

    def add(self, e):
        self.els.append(e)
        return e["id"]

    def cls(self, eid, *names):
        """Queue custom classes for an element. Stamped on by apply_classes()."""
        if eid and names:
            self.classes.setdefault(eid, []).extend(names)

    def apply_classes(self, errors):
        """`customClassnames` is a top-level space-separated string — the editor's own
        custom-class field, so it round-trips (proven, see format.md)."""
        by_id = {e["id"]: e for e in self.els}
        for eid, names in self.classes.items():
            uniq = list(dict.fromkeys(names))
            for c in uniq:
                if not CLASS_RE.fullmatch(c):
                    errors.append(f"{eid}: class {c!r} is not a plain CSS identifier — "
                                  "custom classes ship into a stylesheet selector")
            if eid in by_id:
                by_id[eid]["customClassnames"] = " ".join(uniq)

    # -- shared fragments
    @staticmethod
    def _mob():
        return {"geometry": {"visible": True}, "style": {"background": {"imageFixed": False}}}

    @staticmethod
    def _effect(shadow=False):
        return {"enabledTypes": ["dropShadow"] if shadow else ["none"], "opacity": 22,
                "color": "000000", "offset": {"left": 0, "top": 12}, "blurRadius": 34}

    def root(self, bg, ink, link):
        self.els.insert(0, {
            "id": "lp-pom-root", "type": "lp-pom-root", "name": "Page Root", "containerId": None,
            "style": {"background": {"backgroundColor": bg},
                      "defaults": {"linkDecoration": "none", "color": ink, "linkColor": link},
                      "newBackground": {"type": "solidColor", "solidColor": {"bgColor": bg},
                                        "gradient": {"baseColor": bg}}},
            "geometry": {"position": "relative", "margin": "auto",
                         "contentWidth": BP["desktop"]["canvas"],
                         "visible": True, "scale": 1, "padding": {"top": 0}},
            "breakpoints": {"mobile": {
                "geometry": {"visible": True, "contentWidth": BP["mobile"]["canvas"]},
                "style": {"background": {"imageFixed": False},
                          "newBackground": {"solidColor": {}, "gradient": {}}},
                "confirmationViewed": False}},
            "confirmationViewed": True, "grid": {"showGrid": True},
        })

    def block(self, name, height, bg, mobile_height):
        d, m = BP["desktop"], BP["mobile"]
        eid = self.nid("pom-block")
        grid = lambda b: {"columns": b["cols"], "rowHeight": b["rh"], "xGap": 12, "yGap": 0,
                          "padding": {"top": 0, "right": b["pad"], "bottom": 0, "left": b["pad"]},
                          "snapToGrid": True}
        return self.add({
            "name": name, "id": eid, "type": "lp-pom-block", "containerId": "lp-pom-root",
            "style": {"background": {"backgroundColor": bg, "opacity": 100},
                      "newBackground": {"type": "solidColor", "solidColor": {"bgColor": bg}}},
            "geometry": {"position": "relative",
                         "margin": {"left": "auto", "right": "auto", "bottom": 0},
                         "offset": {"left": 0, "top": 0}, "borderLocation": "outside",
                         "borderApply": {"top": True, "right": True, "bottom": True, "left": True},
                         "backgroundImageApply": False,
                         "savedBorderState": {"left": True, "right": True},
                         "fitWidthToPage": True,
                         "size": {"width": d["canvas"], "height": height},
                         "visible": True, "scale": 1},
            "grid": grid(d),
            "breakpoints": {"mobile": {
                "geometry": {"visible": True,
                             "size": {"width": m["canvas"], "height": mobile_height}},
                "style": {"background": {"imageFixed": False}},
                "grid": grid(m)}},
        })

    def text(self, html, g, container, z, bg, bg_op, valign="baseline"):
        eid = self.nid("pom-text")
        return self.add({
            "name": g["name"], "id": eid, "type": "lp-pom-text", "containerId": container,
            "betterLineHeight": True,
            "style": {"background": {"backgroundColor": bg, "opacity": bg_op},
                      "newBackground": {"type": "solidColor", "solidColor": {}},
                      "effect": {"enabledTypes": ["none"], "opacity": 25, "color": "000000",
                                 "offset": {"left": 0, "top": 4}, "blurRadius": 4}},
            "geometry": self._geo(g, z, extra={"verticalAlign": valign,
                                               "minSize": {"width": 20, "height": 0}}),
            "content": {"text": html, "valid": True, "errors": [], "fonts": []},
            # scale MUST stay numeric: the live renderer rejects the string "fit" and drops
            # the WHOLE page's mobile layout to desktop.
            "breakpoints": {"mobile": self._mobgeo(g, scale=1)},
        })

    def box(self, g, container, z, bg, opacity, radius, border, shadow):
        style = {"background": {"backgroundColor": bg, "opacity": opacity},
                 "newBackground": {"type": "solidColor", "solidColor": {"bgColor": bg}},
                 "effect": self._effect(shadow)}
        if border:
            style["border"] = border
        return self.add({
            "name": g["name"], "id": self.nid("pom-box"), "type": "lp-pom-box",
            "containerId": container, "style": style,
            "geometry": self._geo(g, z, position_border="inside", extra={
                "borderApply": {"top": True, "right": True, "bottom": True, "left": True},
                "layout": None, "cornerRadius": radius}),
            "breakpoints": {"mobile": self._mobgeo(g)},
        })

    def image(self, asset, g, container, z, fit, url):
        eid = self.nid("pom-image")
        if fit:
            self.fit.add(fit)
            self.cls(eid, f"fit-{fit}")
        w, h = g["w"], g["h"]
        return self.add({
            "name": g["name"], "id": eid, "type": "lp-pom-image", "containerId": container,
            "geometry": self._geo(g, z, extra={
                "maintainAR": fit != "cover",
                "transform": {"offset": {"left": 0, "top": 0}, "size": {"width": w, "height": h},
                              "quality": {"compressPng": True, "globalOverride": False}}}),
            "style": {"effect": {"enabledTypes": ["none"], "opacity": 25, "color": "000000",
                                 "offset": {"left": 0, "top": 4}, "blurRadius": 4},
                      "background": {"backgroundColor": "ffffff", "opacity": 0}},
            "action": {"type": "url", "url": url or "", "target": "_self"},
            "content": {"asset": asset, "target": "_self"},
            "lightboxSize": {"width": 840, "height": 480},
            "breakpoints": {"mobile": self._mobgeo(g)},
        })

    def button(self, label, g, container, z, url, action, s):
        bg, hover = s["bg"], s["hover"]
        return self.add({
            "name": g["name"], "id": self.nid("pom-button"), "type": "lp-pom-button",
            "containerId": container, "content": {"label": label},
            "style": {"fontSize": s["size"], "fontWeight": s["weight"],
                      "fontFamily": s["family"], "textShadow": False, "highlight": False,
                      "fillType": "solid", "autoGradient": False,
                      "letterSpacing": s["tracking"], "textTransform": s["transform"],
                      "effect": {"enabledTypes": ["none"], "opacity": 25, "color": "000000",
                                 "offset": {"left": 0, "top": 4}, "blurRadius": 4},
                      "up": {"backgroundColor": bg, "opacity": 100,
                             "gradient": {"type": "custom-gradient", "from": bg, "to": bg},
                             "color": s["color"], "border": {"style": "none"}},
                      "hover": {"backgroundColor": hover,
                                "gradient": {"type": "custom-gradient", "from": hover, "to": hover}},
                      "active": {"auto": True},
                      "background": {"backgroundColor": "ffffff", "opacity": 0},
                      "textStyles": {"strong": True}},
            "geometry": self._geo(g, z, position_border="inside",
                                  extra={"cornerRadius": s["radius"]}),
            "action": {"type": action, "url": url, "target": "_self"},
            "lightboxSize": {"width": 840, "height": 480},
            "breakpoints": {"mobile": self._mobgeo(g)},
            "computations": {"labelHeight": 19},
        })

    def code(self, html, g, container, z):
        return self.add({
            "name": g["name"], "id": self.nid("code"), "type": "lp-code",
            "containerId": container,
            "geometry": {"position": "absolute", "offset": {"left": g["x"], "top": g["y"]},
                         "size": {"width": g["w"], "height": g["h"]},
                         "visible": True, "scale": 1, "zIndex": z},
            "content": {"type": None, "html": html, "valid": True},
            "style": {"background": {"backgroundColor": "ffffff", "opacity": 0}},
            "breakpoints": {"mobile": self._mobgeo(g)},
        })

    def form(self, g, container, z, fields, submit, body_font):
        """Native lp-pom-form. publishedStyles is TOP-LEVEL (not under content) and the
        mobile copy must be an independent list — sharing it halves desktop field widths."""
        fid = self.nid("pom-form")
        out, uuids = [], []
        for f in fields:
            itype = (f.get("type") or "text").lower()
            lptype, val = INPUT_LPTYPE[itype]
            u = str(uuid.uuid4())
            uuids.append(u)
            fd = {"name": f.get("data-label") or f.get("placeholder") or f.get("name", "Field"),
                  "id": f.get("name") or f.get("id"), "placeholder": f.get("placeholder", ""),
                  "type": "text", "lpType": lptype,
                  "show": {"phone": bool(val.get("phone")), "email": bool(val.get("email"))},
                  "validations": dict({"required": "required" in f}, **val), "uuid": u}
            if val.get("phone"):
                fd["validationType"] = "north-american"
            out.append(fd)
        # publishedStyles is DERIVED from the form chrome below — the editor recomputes it on
        # save, so hard-coded values silently drift (found by round-trip diff). See format.md.
        # ponytail: label height fitted to two observations (font 11 -> 12, 14 -> 15).
        label_size, label_gap, field_h, border_w, field_gap = 11, 4, 44, 1, 18
        label_h = round(label_size * 1.1)
        input_h = field_h + 2 * border_w
        input_top = label_h + label_gap
        container_h = input_top + input_h
        stride = container_h + field_gap
        pub = lambda w: [s for i, f in enumerate(out) for s in (
            {"selector": f"#container_{f['id']}", "top": i * stride, "left": 0, "width": w,
             "height": container_h},
            {"selector": f".lp-pom-form-field .ub-input-item.single.form_elem_{f['id']}",
             "top": input_top, "left": 0, "width": w, "height": input_h},
            {"selector": f"#label_{f['id']}", "top": 0, "left": 0, "width": w, "height": label_h})]
        submit_id = self.nid("pom-button")
        self.add({
            "name": g["name"], "id": fid, "type": "lp-pom-form", "containerId": container,
            "style": {"label": {"font": {"size": label_size, "family": body_font, "weight": 600,
                                         "style": "normal", "textStyles": {"strong": True}},
                                "color": "888888", "centerAlign": False},
                      "cbxlabel": {"font": {"size": 13, "family": body_font, "weight": 400,
                                            "style": "normal"}, "color": "000"},
                      "field": {"innerShadow": False, "backgroundColor": "fafafa",
                                "color": "222222"},
                      "background": {"backgroundColor": "ffffff", "opacity": 0}},
            "geometry": self._geo(g, z, extra={
                "label": {"calculatedWidth": 0, "margin": {"bottom": label_gap, "right": 12},
                          "alignment": "top"},
                "field": {"height": field_h, "width": 100, "groupWidth": 100,
                          "margin": {"bottom": field_gap}, "fontSize": 14, "cornerRadius": 6,
                          "border": {"color": "d6d6d2", "style": "solid", "width": border_w}},
                "buttonPlacement": "auto", "progressBarPlacement": "auto"}),
            "content": {"submitButtonText": submit["label"], "confirmAction": "modal",
                        "confirmMessage": submit.get("confirm", "Thanks — we'll be in touch."),
                        "passParams": False, "buttonId": submit_id, "previousButtonId": None,
                        "nextButtonId": None, "progressBarId": None, "fields": out,
                        "steps": [{"uuid": str(uuid.uuid4()), "fieldUUIDs": uuids}],
                        "confirmTarget": "", "confirmationPage": "a-form_confirmation.html",
                        "confirmationPageSize": {"desktop": {"height": 180, "width": 512},
                                                 "mobile": {"height": 180, "width": 240}}},
            "lightboxSize": {"width": 840, "height": 480},
            "publishedStyles": pub(g["w"]),
            "breakpoints": {"mobile": dict(self._mobgeo(g),
                                           publishedStyles=pub(g["mw"] or g["w"]))},
        })
        sg = submit["geo"]
        self.add({
            "name": "Form Submit Button", "id": submit_id, "type": "lp-pom-button",
            "containerId": fid, "content": {"label": submit["label"]},
            "style": {"fontSize": submit["size"], "fontWeight": submit["weight"],
                      "fontFamily": submit["family"], "textShadow": False, "highlight": False,
                      "fillType": "solid", "autoGradient": False,
                      "textTransform": submit["transform"], "letterSpacing": submit["tracking"],
                      "effect": {"enabledTypes": ["none"], "opacity": 25, "color": "000000",
                                 "offset": {"left": 0, "top": 4}, "blurRadius": 4},
                      "up": {"backgroundColor": submit["bg"], "opacity": 100,
                             "gradient": {"type": "custom-gradient", "from": submit["bg"],
                                          "to": submit["bg"]},
                             "color": submit["color"], "border": {"style": "none"}},
                      "hover": {"backgroundColor": submit["hover"],
                                "gradient": {"type": "custom-gradient", "from": submit["hover"],
                                             "to": submit["hover"]}},
                      "active": {"auto": True},
                      "background": {"backgroundColor": "ffffff", "opacity": 0},
                      "textStyles": {"strong": True}},
            "geometry": self._geo(sg, 7, position_border="inside",
                                  extra={"cornerRadius": submit["radius"]}),
            "action": {"type": "form", "url": "", "target": "_self"},
            "lightboxSize": {"width": 840, "height": 480},
            "breakpoints": {"mobile": self._mobgeo(sg)},
            "computations": {"labelHeight": 19},
            "constraints": {"removable": False, "copyable": False, "allowActions": ["form"]},
        })
        return fid

    def stylesheet(self, accent):
        rules = ["a{text-decoration:none}",
                 ".lp-pom-form-field input:focus,.lp-pom-form-field textarea:focus"
                 f"{{outline:2px solid #{accent};outline-offset:0;background:#fff}}"]
        # native lp-pom-image STRETCHES to its box — object-fit is the only way to crop.
        # Target a class, never a list of ids: one rule however many images, and the client
        # can add or remove `fit-cover` on an element from the editor's custom-class field.
        for how in sorted(self.fit):
            rules.append(f".fit-{how} img{{width:100%!important;height:100%!important;"
                         f"object-fit:{how}!important}}")
        self.add({"name": "Stylesheet 1", "containerId": None, "placement": "body:after",
                  "content": {"type": None, "html": "<style>\n" + "\n".join(rules) + "\n</style>",
                              "valid": True},
                  "breakpoints": {}, "id": self.nid("stylesheet"), "type": "lp-stylesheet"})

    # -- geometry helpers
    @staticmethod
    def _geo(g, z, position_border="outside", extra=None):
        geo = {"position": "absolute", "offset": {"left": g["x"], "top": g["y"]},
               "size": {"width": g["w"], "height": g["h"]},
               "borderLocation": position_border, "visible": True, "scale": 1, "zIndex": z}
        geo.update(extra or {})
        return geo

    @staticmethod
    def _mobgeo(g, scale=1):
        if not g["visible"]:
            return {"geometry": {"visible": False},
                    "style": {"background": {"imageFixed": False}}}
        return {"geometry": {"visible": True,
                             "offset": {"left": g["mx"], "top": g["my"]},
                             "size": {"width": g["mw"], "height": g["mh"]}, "scale": scale},
                "style": {"background": {"imageFixed": False}}}


# ---------------------------------------------------------------- validators
def validate(els, errors, warnings):
    """Hard errors, never silent fixes. Grid conformance is graded by consequence:
    positions error (a client click would jump the element), widths warn, heights free."""
    by_id = {e["id"]: e for e in els}
    forms = [e for e in els if e["type"] == "lp-pom-form"]
    if len(forms) != 1:
        errors.append(f"exactly one form per page (Classic hard limit); found {len(forms)}")
    for f in forms:
        sb = f["content"]["buttonId"]
        if by_id.get(sb, {}).get("containerId") != f["id"]:
            errors.append(f"{sb}: submit button must be a child of {f['id']}")

    def abspos(e, bp):
        """Block-relative absolute position, and the owning block."""
        x = y = 0
        cur = e
        while cur is not None and cur["type"] not in ("lp-pom-block", "lp-pom-root"):
            g = (cur["breakpoints"]["mobile"].get("geometry") if bp == "mobile"
                 else cur["geometry"])
            g = g if g and g.get("offset") else cur["geometry"]
            x += g["offset"]["left"]
            y += g["offset"]["top"]
            cur = by_id.get(cur.get("containerId"))
        return x, y, cur

    for e in els:
        if e["type"] in ("lp-pom-root", "lp-stylesheet", "lp-pom-block"):
            continue
        parent = by_id.get(e.get("containerId"))
        # Grid conformance applies to a block's DIRECT children only. A box and the content
        # inside it cannot both sit on the grid unless the padding happens to be a whole grid
        # unit, so the card rides the grid and its contents keep their padding (the proven
        # group-snap rule). Nested offsets are the designer's padding, not grid positions.
        nested = parent is None or parent["type"] != "lp-pom-block"
        for bp, cfg in BP.items():
            g = (e["breakpoints"]["mobile"].get("geometry") if bp == "mobile" else e["geometry"])
            if bp == "mobile" and not g.get("visible", True):
                continue
            if not g or not g.get("offset"):
                continue
            w, h = g["size"]["width"], g["size"]["height"]
            x, y, _ = abspos(e, bp)
            if x + w > cfg["canvas"] + 1:
                errors.append(f"{e['id']} [{bp}]: right edge {x + w:.0f} exceeds "
                              f"canvas {cfg['canvas']}")
            if nested or w >= cfg["canvas"] * 0.98:
                continue                                   # nested / full-bleed: exempt
            if (x - cfg["pad"]) % cfg["pitch"] not in (0, cfg["colw"]):
                errors.append(f"{e['id']} [{bp}]: left {x:.0f} is off the column grid "
                              f"(lines at {cfg['pad']}+{cfg['pitch']}k and +{cfg['colw']})")
            if y % cfg["rh"]:
                errors.append(f"{e['id']} [{bp}]: top {y:.0f} is not a multiple of "
                              f"{cfg['rh']}px (row grid)")
            if (w - cfg["colw"]) % cfg["pitch"]:
                warnings.append(f"{e['id']} [{bp}]: width {w:.0f} is not a whole span "
                                f"({cfg['pitch']}n-12)")
    for e in els:
        for g in (e.get("geometry"),
                  e.get("breakpoints", {}).get("mobile", {}).get("geometry")):
            if isinstance(g, dict) and isinstance(g.get("scale"), str):
                errors.append(f"{e['id']}: scale must be numeric, never the string "
                              f"{g['scale']!r} (live renderer drops mobile entirely)")
        c = e.get("containerId")
        if c is not None and c not in by_id:
            errors.append(f"{e['id']}: dangling containerId {c}")


# ---------------------------------------------------------------- archive
def make_asset(src_path, nat, company_id):
    """Asset JSON record. Mirrors a genuine export exactly — that shape is what makes
    new-asset ingestion work. The file copy happens in write_archive()."""
    name = os.path.basename(src_path)
    u = str(uuid.uuid4())
    base, ext = os.path.splitext(name)
    ext = ext.lstrip(".").lower()
    ctype = {"webp": "image/webp", "png": "image/png", "jpg": "image/jpeg",
             "jpeg": "image/jpeg", "gif": "image/gif",
             "svg": "image/svg+xml"}.get(ext, "image/png")
    return {"company_id": company_id, "uuid": u,
            "unique_url": f"/assets/{u}/{uuid.uuid4().hex[:8]}-{name}",
            "content_url": f"/assets/{u}/{base}.original.{ext}?1779210799",
            "content_content_type": ctype, "name": name,
            "content_file_size": os.path.getsize(src_path),
            "size": {"width": nat[0], "height": nat[1]}, "sizeVerified": True}


def write_archive(out, page_name, els, fonts, in_use, assets):
    """Build the archive tree from scratch — no account-specific skeleton to clone."""
    arc = uuid.uuid4().hex[:16]
    page_id, source_uuid = uuid.uuid4().hex[:16], str(uuid.uuid4())
    work = out + ".work"
    if os.path.exists(work):
        shutil.rmtree(work)
    root = os.path.join(work, arc)
    variant = os.path.join(root, "pages", page_id, "page_variants", "a")
    conf = os.path.join(variant, "sub_pages", uuid.uuid4().hex[:16])
    os.makedirs(os.path.join(root, "assets"), exist_ok=True)
    os.makedirs(os.path.join(conf, "page_variants", "a"), exist_ok=True)

    def dump(p, obj):
        with open(p, "w") as fh:
            json.dump(obj, fh, separators=(",", ":"))

    def sidecars(d):
        open(os.path.join(d, "styles.json"), "w").close()
        open(os.path.join(d, "javascripts.json"), "w").close()
        open(os.path.join(d, "keywords.json"), "w").close()
        dump(os.path.join(d, "attachments.json"), {"uuids": []})

    settings = lambda ref, width, extra: dict({
        "defaultWidth": width, "showPageTransformBox": True, "showSectionBoundaries": True,
        "showPageSectionProtrusionWarnings": True,
        # master switch: without this, phones are served the DESKTOP layout
        "multipleBreakpointsEnabled": True,
        "contentType": "pageVariant",
        "activeGoals": [{"type": "form", "url": "/fs", "sortOrder": 1}],
        "builderVersion": "v6.24.319", "globalImageQuality": {"value": 60, "compressPng": True},
        "refId": ref, "webFontsInUse": {}, "webFontsExternalInUse": {},
        "tabletBreakpointDisabled": True, "multipleBreakpointsVisibility": True,
        # we ship no lightbox sub-page; true here makes the LIVE renderer hunt for
        # missing lightbox data and collapse mobile to the desktop layout
        "hasLightbox": False,
    }, **extra)

    dump(os.path.join(root, "pages", page_id, "source.json"), {"source_uuid": source_uuid})
    dump(os.path.join(root, "pages", page_id, "metadata.json"),
         {"name": page_name, "champion_variant_id": "a"})
    dump(os.path.join(variant, "metadata.json"), {
        "name": "First Variant", "title": "", "description": "", "keywords": "",
        "variant_id": "a", "variant_weight": 100, "type": "PageVariant",
        "last_element_id": max(int(e["id"].rsplit("-", 1)[-1])
                               for e in els if e["id"] != "lp-pom-root"),
        "has_form": True, "version": "4.2", "template_id": 0})
    dump(os.path.join(variant, "settings.json"),
         settings(1, 760, {"fonts": fonts, "webFontsInUse": in_use, "noRobots": True}))
    dump(os.path.join(variant, "elements.json"), els)
    sidecars(variant)

    dump(os.path.join(conf, "metadata.json"),
         {"name": "Form Confirmation Page", "used_as": "form_confirmation",
          "path_name": "a-form_confirmation.html", "champion_variant_id": "a"})
    cv = os.path.join(conf, "page_variants", "a")
    dump(os.path.join(cv, "metadata.json"), {
        "name": "Form Confirmation Page", "title": "", "description": "", "keywords": "",
        "variant_id": "a", "variant_weight": 100, "type": "PageVariant",
        "last_element_id": 2, "has_form": False, "version": "4.2", "template_id": None})
    dump(os.path.join(cv, "settings.json"), settings(2, 512, {
        "activeGoals": [], "mainPage": {"uuid": source_uuid, "variant_id": "a"}}))
    dump(os.path.join(cv, "elements.json"), CONFIRMATION_ELEMENTS)
    sidecars(cv)

    for src, asset in assets:
        d = os.path.join(root, "assets", asset["uuid"])
        os.makedirs(d, exist_ok=True)
        shutil.copy(src, os.path.join(d, asset["name"]))

    def norm(ti):
        if os.path.basename(ti.name) == ".DS_Store":
            return None
        ti.uid = ti.gid = 0
        ti.uname, ti.gname = "nobody", "nogroup"
        ti.mode = 0o755 if ti.isdir() else 0o644   # real exports ship 0644 files
        return ti

    if os.path.exists(out):
        os.remove(out)
    with tarfile.open(out, "w", format=tarfile.GNU_FORMAT) as t:
        t.add(root, arcname=arc, filter=norm)
    shutil.rmtree(work)


CONFIRMATION_ELEMENTS = [
    {"name": "New Page Root", "id": "lp-pom-root", "type": "lp-pom-root", "containerId": None,
     "style": {"background": {"backgroundColor": "eee", "opacity": 100},
               "newBackground": {"type": "solidColor", "solidColor": {}},
               "defaults": {"color": "000", "linkColor": "0000ff", "linkDecoration": "none"}},
     "geometry": {"position": "relative", "backgroundImageApply": False, "margin": "auto",
                  "contentWidth": 512, "visible": True, "scale": 1, "padding": {"top": 0}},
     "grid": {"showGrid": True},
     "breakpoints": {"mobile": {"geometry": {"visible": True, "contentWidth": 240},
                                "style": {"background": {"imageFixed": False}},
                                "confirmationViewed": False}},
     "confirmationViewed": False},
    {"name": "Section 1", "id": "lp-pom-block-1", "type": "lp-pom-block",
     "containerId": "lp-pom-root",
     "style": {"background": {"backgroundColor": "fff", "opacity": 100},
               "newBackground": {"type": "solidColor", "solidColor": {}}},
     "geometry": {"position": "relative", "margin": {"left": "auto", "right": "auto", "bottom": 0},
                  "offset": {"left": 0, "top": 0}, "borderLocation": "outside",
                  "borderApply": {"top": True, "right": True, "bottom": True, "left": True},
                  "backgroundImageApply": False,
                  "savedBorderState": {"left": True, "right": True}, "fitWidthToPage": False,
                  "size": {"width": 512, "height": 180}, "visible": True, "scale": 1},
     "grid": {"columns": 6, "rowHeight": 24, "xGap": 12, "yGap": 12,
              "padding": {"top": 36, "right": 56, "bottom": 36, "left": 56}, "snapToGrid": False},
     "breakpoints": {"mobile": {"grid": {"columns": 6, "rowHeight": 24, "xGap": 12, "yGap": 12,
                                         "padding": {"top": 36, "right": 12, "bottom": 36,
                                                     "left": 12}},
                                "geometry": {"visible": True},
                                "style": {"background": {"imageFixed": False}}}}},
    {"name": "Text 1", "id": "lp-pom-text-2", "type": "lp-pom-text",
     "containerId": "lp-pom-block-1", "betterLineHeight": True,
     "style": {"background": {"backgroundColor": "fff", "opacity": 0},
               "newBackground": {"type": "solidColor", "solidColor": {}},
               "effect": {"enabledTypes": ["none"], "opacity": 25, "color": "000000",
                          "offset": {"left": 0, "top": 4}, "blurRadius": 4}},
     "geometry": {"position": "absolute", "offset": {"left": 20, "top": 52.5},
                  "size": {"width": 472, "height": 75}, "borderLocation": "outside",
                  "verticalAlign": "baseline", "visible": True, "scale": 1,
                  "minSize": {"width": 20, "height": 0}, "zIndex": 1},
     "content": {"text": '<h1 style="text-align: center;">Thank You!</h1>'
                         '<p style="text-align: center;">Your form has been submitted.</p>',
                 "valid": True, "errors": [], "fonts": []},
     "breakpoints": {"mobile": {"geometry": {"scale": 1, "visible": True,
                                             "size": {"width": 200, "height": 75}},
                                "style": {"background": {"imageFixed": False}}}}},
]


# ---------------------------------------------------------------- walk
def geo_of(node, mrules, errors, name):
    s, m = node["style"], mrules.get(node["id"], {})
    g = {"name": name,
         "x": px(s.get("left"), 0), "y": px(s.get("top"), 0),
         "w": px(s.get("width"), 0), "h": px(s.get("height"), 0),
         "visible": m.get("display", "").strip() != "none"}
    if not g["visible"]:
        g.update(mx=g["x"], my=g["y"], mw=g["w"], mh=g["h"])
        return g
    if not m:
        errors.append(f"#{node['id']}: no mobile rule in the @media block "
                      f"(give it geometry or display:none)")
    g.update(mx=px(m.get("left"), g["x"]), my=px(m.get("top"), g["y"]),
             mw=px(m.get("width"), g["w"]), mh=px(m.get("height"), g["h"]))
    return g


def transcribe(html_path, out_path, page_name, company_id):
    src = open(html_path).read()
    p = Design()
    p.feed(src)
    errors, warnings = list(p.errors), []
    mrules = media_rules("".join(p.css), errors)
    fonts, in_use = parse_fonts(p.font_href)
    if not fonts:
        errors.append("no Google Fonts <link> found — fonts are derived from it")

    body = p.body
    b = Build()
    ink = hexcolor(body.get("data-ink"), "000000")
    accent = hexcolor(body.get("data-accent"), "3366cc")
    b.root(hexcolor(body.get("data-bg"), "ffffff"), ink, hexcolor(body.get("data-link"), accent))
    body_font = (body.get("data-body-font")
                 or (list(in_use)[-1] if in_use else "Open Sans"))
    assets, base = [], os.path.dirname(os.path.abspath(html_path))
    asset_by_path = {}                                # realpath -> asset record (dedup)
    lp_of = {}                                        # design id -> lp id
    z = [0]

    def emit(node, container):
        z[0] += 1
        name = node["attrs"].get("data-name") or node["lp"].title()
        g = geo_of(node, mrules, errors, name)
        s = node["style"]
        bg = hexcolor(s.get("background-color") or s.get("background"))
        inner = "".join(node["inner"]).strip()
        lp = node["lp"]
        if lp == "text":
            eid = b.text(inner, g, container, z[0], bg or "ffffff",
                         100 if bg else 0, s.get("vertical-align", "baseline"))
        elif lp == "box":
            border = None
            if s.get("border"):
                bw = px(s["border"], 0)
                border = {"style": "solid", "width": bw,
                          "color": hexcolor(s["border"], "cccccc")}
            eid = b.box(g, container, z[0], bg or "ffffff",
                        int(float(s.get("opacity", 1)) * 100) if bg else 0,
                        px(s.get("border-radius"), 0), border,
                        "box-shadow" in s)
        elif lp == "image":
            srcp = os.path.join(base, node["attrs"].get("src", ""))
            nat = node["attrs"].get("data-nat", "")
            if "x" not in nat:
                errors.append(f"#{node['id']}: needs data-nat=\"WIDTHxHEIGHT\" "
                              f"(natural pixel size — measure.mjs reports it)")
                nat = "0x0"
            if not os.path.exists(srcp):
                errors.append(f"#{node['id']}: asset not found: {srcp}")
                return
            wh = [int(px(v, 0)) for v in nat.split("x")[:2]]
            # one record per source file — real exports share one asset uuid across
            # elements (Maddy's export: 6 images -> 1 asset)
            key = os.path.realpath(srcp)
            asset = asset_by_path.get(key)
            if asset is None:
                asset = asset_by_path[key] = make_asset(srcp, wh, company_id)
                assets.append((srcp, asset))
            eid = b.image(asset, g, container, z[0],
                          node["attrs"].get("data-fit"), node["attrs"].get("href"))
        elif lp in ("button", "submit"):
            eid = None                                # handled by the form for 'submit'
            style = btn_style(s, accent, ink, body_font)
            if lp == "button":
                href = node["attrs"].get("href", "")
                eid = b.button(node["attrs"].get("data-label") or label_text(inner)
                               or "Button", g,
                               container, z[0], href,
                               "url", style)
        elif lp == "code":
            eid = b.code(inner, g, container, z[0])
        elif lp == "form":
            sub = next((k for k in node["kids"] if k["lp"] == "submit"), None)
            if sub is None:
                errors.append(f"#{node['id']}: form needs a child with data-lp-type=\"submit\"")
                return
            st = btn_style(sub["style"], accent, ink, body_font)
            st.update(label=(sub["attrs"].get("data-label")
                             or label_text("".join(sub["inner"])) or "Submit"),
                      geo=geo_of(sub, mrules, errors, "Form Submit Button"),
                      confirm=node["attrs"].get("data-confirm"))
            if not st["confirm"]:
                st.pop("confirm")
            for f in node["fields"]:
                t = (f.get("type") or "text").lower()
                if t not in INPUT_LPTYPE:
                    errors.append(f"#{node['id']}: <input type=\"{t}\"> has no verified "
                                  f"lpType — use text/email/tel, or add it in the editor")
            eid = b.form(g, container, z[0],
                         [f for f in node["fields"]
                          if (f.get("type") or "text").lower() in INPUT_LPTYPE],
                         st, body_font)
        else:
            return
        if eid:
            lp_of[node["id"]] = eid
            b.cls(eid, *node["attrs"].get("class", "").split())
        for kid in node["kids"]:
            if kid["lp"] != "submit":
                emit(kid, eid or container)

    for node in p.nodes:
        if node["parent"] is None:
            if node["lp"] != "block":
                errors.append(f"#{node['id']}: top-level elements must be "
                              f"data-lp-type=\"block\" sections")
                continue
            g = geo_of(node, mrules, errors, node["attrs"].get("data-name") or "Section")
            bid = b.block(g["name"], g["h"] or px(node["style"].get("height"), 0),
                          hexcolor(node["style"].get("background-color")
                                   or node["style"].get("background"), "ffffff"),
                          g["mh"])
            lp_of[node["id"]] = bid
            b.cls(bid, *node["attrs"].get("class", "").split())
            for kid in node["kids"]:
                emit(kid, bid)
    b.stylesheet(accent)
    b.apply_classes(errors)

    # resolve in-page anchors (#design-id -> #lp-pom-form-N)
    for e in b.els:
        u = e.get("action", {}).get("url", "")
        if u.startswith("#") and u[1:] in lp_of:
            e["action"]["url"] = "#" + lp_of[u[1:]]
        elif u.startswith("#") and not u[1:].startswith("lp-pom"):
            errors.append(f"{e['id']}: anchor {u} does not match any design element id")

    validate(b.els, errors, warnings)
    # validate() names generated lp ids; translate back to design ids so the designer can
    # act on an error without a lookup table (bakeoff arm a had to build one by hand)
    of_lp = {v: "#" + k for k, v in lp_of.items()}
    xlate = lambda s: re.sub(r"\blp-(?:pom-[a-z]+|code|stylesheet)-\d+\b",
                             lambda m: of_lp.get(m.group(), m.group()), s)
    warnings = [xlate(w) for w in warnings]
    errors = [xlate(e) for e in errors]
    for w in warnings:
        print(f"  warn: {w}", file=sys.stderr)
    if errors:
        print(f"\n{len(errors)} error(s) — nothing written:", file=sys.stderr)
        for e in dict.fromkeys(errors):
            print(f"  ERROR {e}", file=sys.stderr)
        return 1
    write_archive(out_path, page_name, b.els, fonts, in_use, assets)
    print(f"OK  {len(b.els)} elements -> {out_path}")
    return 0


def btn_style(s, accent, ink, body_font):
    bg = hexcolor(s.get("background-color") or s.get("background"), accent)
    return {"bg": bg, "hover": hexcolor(s.get("--hover"), None) or darken(bg),
            "color": hexcolor(s.get("color"), ink),
            "radius": px(s.get("border-radius"), 0),
            "family": f"{(s.get('font-family') or body_font).split(',')[0].strip().strip(chr(39))},"
                      f" sans-serif",
            "size": str(int(px(s.get("font-size"), 14))),
            "weight": int(px(s.get("font-weight"), 700)),
            "transform": s.get("text-transform", "none"),
            "tracking": s.get("letter-spacing", "0")}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("design")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--page-name", default=None)
    ap.add_argument("--company-id", type=int, default=0,
                    help="Unbounce company_id for asset records. 0 works; if asset "
                         "ingestion fails, lift the real one from an export of the account.")
    a = ap.parse_args()
    out = a.out or os.path.splitext(a.design)[0] + ".unbounce"
    name = a.page_name or os.path.splitext(os.path.basename(a.design))[0]
    return transcribe(a.design, out, name, a.company_id)


if __name__ == "__main__":
    sys.exit(main())
