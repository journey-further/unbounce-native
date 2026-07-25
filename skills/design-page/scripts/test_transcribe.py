#!/usr/bin/env python3
"""One runnable check for transcribe.py: a conformant design builds, and each validator
fires on the design that violates it.  Run: python3 test_transcribe.py"""
import io, json, os, re, shutil, struct, sys, tarfile, tempfile, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import transcribe as T


def png(w, h):
    """Smallest valid greyscale PNG — a real decodable image, so measure.mjs can read
    naturalWidth off it too."""
    def chunk(kind, data):
        c = kind + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))
    raw = b"".join(b"\0" + b"\xff" * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


PNG = png(4, 3)

# 70 + 48k column lines; tops multiples of 12; widths 48n-12.  Mobile: 10 + 52k, widths 52n-12.
GOOD = """<!doctype html><html><head>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;700&family=Open+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>
@media (max-width:600px){
body, section { width:320px; }
#hero { height: 936px !important; }
#bg { left: 0 !important; top: 0 !important; width: 320px !important; height: 900px !important; }
#h1 { left: 10px !important; top: 36px !important; width: 300px !important; height: 200px !important; }
#deco { display: none !important; }
#card { left: 10px !important; top: 264px !important; width: 300px !important; height: 540px !important; }
#f { left: 10px !important; top: 12px !important; width: 280px !important; height: 420px !important; }
#sub { left: 0 !important; top: 368px !important; width: 280px !important; height: 52px !important; }
#cta { left: 10px !important; top: 828px !important; width: 196px !important; height: 48px !important; }
#note { left: 10px !important; top: 900px !important; width: 300px !important; height: 24px !important; }
}
</style></head>
<body data-accent="#99cc00" data-ink="#1d2327">
<section id="hero" data-lp-type="block" data-name="Hero" style="height:720px;background:#1d2327">
  <img id="bg" data-lp-type="image" data-fit="cover" data-nat="1200x800" src="a.png"
       class="hero-media" style="left:0;top:0;width:1280px;height:720px">
  <div id="h1" data-lp-type="text" style="left:70px;top:96px;width:564px;height:132px">
    <p><span style="font-family:Oswald;font-size:52px;color:#ffffff">UP TO $2,500 OFF</span></p>
  </div>
  <div id="deco" data-lp-type="code" style="left:70px;top:240px;width:372px;height:12px"><svg></svg></div>
  <div id="card" data-lp-type="box" style="left:694px;top:48px;width:516px;height:588px;background:#ffffff;border-radius:8px">
    <form id="f" data-lp-type="form" style="left:28px;top:24px;width:460px;height:432px">
      <input type="text" name="first_name" placeholder="First name" required>
      <input type="email" name="email" placeholder="Email" required>
      <input type="tel" name="phone" placeholder="Phone" required>
      <button id="sub" data-lp-type="submit" style="left:0;top:380px;width:460px;height:52px;background:#99cc00;color:#1d2327;border-radius:6px;font-family:Oswald;font-size:16px;font-weight:700">Get my free estimate</button>
    </form>
  </div>
  <a id="cta" data-lp-type="button" href="#f" style="left:70px;top:600px;width:180px;height:48px;background:#99cc00;color:#1d2327;border-radius:6px">Get a free estimate</a>
  <div id="note" data-lp-type="text" style="left:70px;top:672px;width:1140px;height:24px"><p>No obligation.</p></div>
</section>
</body></html>"""


def run(html, out="page.unbounce", **kw):
    d = tempfile.mkdtemp()
    open(os.path.join(d, "design.html"), "w").write(html)
    open(os.path.join(d, "a.png"), "wb").write(PNG)
    err = io.StringIO()
    real, sys.stderr = sys.stderr, err
    try:
        rc = T.transcribe(os.path.join(d, "design.html"), os.path.join(d, out),
                          kw.get("name", "Test"), 0)
    finally:
        sys.stderr = real
    return rc, err.getvalue(), os.path.join(d, out)


def elements(path):
    with tarfile.open(path) as t:
        m = next(n for n in t.getnames() if n.endswith("page_variants/a/elements.json"))
        return json.load(t.extractfile(m)), t.getnames()


# ---- the conformant design builds --------------------------------------------
rc, err, out = run(GOOD)
assert rc == 0, f"conformant design failed:\n{err}"
els, names = elements(out)
kinds = [e["type"] for e in els]
assert kinds.count("lp-pom-root") == 1 and kinds.count("lp-pom-block") == 1
assert kinds.count("lp-pom-form") == 1 and kinds.count("lp-pom-image") == 1
assert kinds.count("lp-pom-button") == 2, kinds          # cta + submit
assert kinds.count("lp-stylesheet") == 1

by_id = {e["id"]: e for e in els}
form = next(e for e in els if e["type"] == "lp-pom-form")
card = next(e for e in els if e["type"] == "lp-pom-box")
# nesting: DOM tree IS the containerId tree, offsets stay parent-relative
assert form["containerId"] == card["id"]
assert form["geometry"]["offset"] == {"left": 28, "top": 24}
# submit button is a child of the FORM, not the block (else it clips on mobile)
sub = by_id[form["content"]["buttonId"]]
assert sub["containerId"] == form["id"]
# publishedStyles: top-level, per-breakpoint independent copies, 80px stride.
# The stride/heights are what the editor recomputes on save — see format.md.
assert len(form["publishedStyles"]) == 9 and form["publishedStyles"][0]["width"] == 460
assert form["breakpoints"]["mobile"]["publishedStyles"][0]["width"] == 280
assert form["publishedStyles"] is not form["breakpoints"]["mobile"]["publishedStyles"]
assert [p["top"] for p in form["publishedStyles"][::3]] == [0, 80, 160]
container, item, label = form["publishedStyles"][:3]
assert (container["height"], item["top"], item["height"], label["height"]) == (62, 16, 46, 12)
# proven lpTypes only, validations mapped from the HTML
lp = {f["id"]: (f["lpType"], f["validations"]) for f in form["content"]["fields"]}
assert lp["email"][0] == "single-line-text" and lp["email"][1]["email"] is True
assert lp["phone"][1]["phone"] is True and lp["first_name"][1] == {"required": True}
# hide-on-mobile comes from display:none, not a data attribute
deco = next(e for e in els if e["type"] == "lp-code")
assert deco["breakpoints"]["mobile"]["geometry"]["visible"] is False
# scale is numeric everywhere — a string "fit" kills the live mobile layout
for e in els:
    for g in (e.get("geometry"), e.get("breakpoints", {}).get("mobile", {}).get("geometry")):
        assert not isinstance((g or {}).get("scale"), str), e["id"]
# anchor rewritten to the real form id
cta = next(e for e in els if e["type"] == "lp-pom-button" and e["id"] != sub["id"])
assert cta["action"]["url"] == "#" + form["id"], cta["action"]
# labels come from inner text, tags stripped (data-label overrides — tested below)
assert cta["content"]["label"] == "Get a free estimate", cta["content"]
assert form["content"]["submitButtonText"] == "Get my free estimate", form["content"]
# archive member modes match real exports (0644 files / 0755 dirs, uid 0)
with tarfile.open(out) as t:
    for m in t.getmembers():
        assert m.mode == (0o755 if m.isdir() else 0o644), (m.name, oct(m.mode))
        assert m.uid == 0 and m.uname == "nobody", m.name
# object-fit lands in the stylesheet (native images stretch otherwise), targeting a CLASS —
# an id list is neither reusable nor reachable from the editor's custom-class field
sheet = next(e for e in els if e["type"] == "lp-stylesheet")["content"]["html"]
assert ".fit-cover img{" in sheet and "object-fit:cover" in sheet and "<head>" not in sheet
assert "#lp-pom-image" not in sheet, "stylesheet must not target element ids"
# the derived fit class and the design's own class= both ship, space-separated
img = next(e for e in els if e["type"] == "lp-pom-image")
assert img["customClassnames"] == "fit-cover hero-media", img.get("customClassnames")
# elements with no class carry no key at all (matches a real export)
assert "customClassnames" not in next(e for e in els if e["type"] == "lp-pom-text")
# archive shape + settings flags
with tarfile.open(out) as t:
    s = json.load(t.extractfile(next(n for n in names if n.endswith("a/settings.json")
                                     and "sub_pages" not in n)))
    subs = [json.load(t.extractfile(n)) for n in names
            if "sub_pages" in n and n.endswith("/metadata.json") and "page_variants" not in
            n.split("sub_pages/")[1]]
assert s["multipleBreakpointsEnabled"] is True and s["hasLightbox"] is False
assert s["webFontsInUse"] == {"Oswald": ["400", "700"], "Open Sans": ["400", "600"]}
# exactly one sub-page: the form confirmation. A lightbox sub-page + hasLightbox:true
# collapses the live mobile layout to desktop, so we never ship one.
assert [x["used_as"] for x in subs] == ["form_confirmation"], subs

# ---- every validator fires ---------------------------------------------------
def fails(mutate, needle):
    rc, err, _ = run(mutate(GOOD))
    assert rc == 1 and needle in err, f"expected {needle!r}, got:\n{err}"

fails(lambda h: h.replace("left:70px;top:96px", "left:73px;top:96px"), "off the column grid")
# validator errors name DESIGN ids, not generated lp-pom ids
fails(lambda h: h.replace("left:70px;top:96px", "left:73px;top:96px"), "#h1 [desktop]")
fails(lambda h: h.replace("left:70px;top:96px", "left:70px;top:99px"), "not a multiple of 12")
fails(lambda h: h.replace("width:564px;height:132px", "width:1240px;height:132px"), "exceeds canvas")
fails(lambda h: h.replace("#h1 { left: 10px", "#h1 { left: 34px"), "exceeds canvas")
fails(lambda h: h.replace('<input type="tel"', '<select name="x"></select><input type="tel"'),
      "add the field natively")
fails(lambda h: h.replace('type="tel"', 'type="date"'), "no verified")
fails(lambda h: h.replace('data-lp-type="submit"', 'data-lp-type="button"'), "needs a child")
fails(lambda h: h.replace('href="#f"', 'href="#nope"'), "does not match any design element")
fails(lambda h: re.sub(r"#note \{[^}]*\}", "", h), "no mobile rule")
fails(lambda h: h.replace("#note { left: 10px", "#note { color: red !important; left: 10px"),
      "not allowed in the mobile block")
fails(lambda h: h.replace('<link href="https://fonts.googleapis.com', '<link href="https://x.test'),
      "no Google Fonts")
# !important is load-bearing in the mobile block — but it must not leak into a value
assert T.decls("left: 10px !important; display: none !important") == {"left": "10px",
                                                                     "display": "none"}

# width off-span is a WARNING, not an error
rc, err, _ = run(GOOD.replace("width:180px;height:48px", "width:176px;height:48px"))
assert rc == 0 and "not a whole span" in err, err

# ---- colour tokens are found anywhere in a shorthand, not only at position 0 --
assert T.hexcolor("1px solid #e8e8e8") == "e8e8e8"
assert T.hexcolor("url(x.png) #fff") == "ffffff"
assert T.hexcolor("2px solid rgba(255, 255, 255, .14)") == "ffffff"   # alpha discarded
assert T.hexcolor("none", "cccccc") == "cccccc"
rc, err, out = run(GOOD.replace("background:#ffffff;border-radius:8px",
                                "background:#ffffff;border-radius:8px;border:1px solid #e8e8e8"))
assert rc == 0, err
els, _ = elements(out)
box = next(e for e in els if e["type"] == "lp-pom-box")
assert box["style"]["border"] == {"style": "solid", "width": 1, "color": "e8e8e8"}, box["style"]

# ---- data-label overrides inner text on buttons -------------------------------
rc, err, out = run(GOOD.replace('<a id="cta" data-lp-type="button"',
                                '<a id="cta" data-lp-type="button" data-label="Call now"'))
assert rc == 0, err
els, _ = elements(out)
cta = next(e for e in els if e["type"] == "lp-pom-button" and e["action"]["type"] == "url")
assert cta["content"]["label"] == "Call now", cta["content"]

# ---- one source file -> one asset record, however many <img>s reuse it --------
two = GOOD.replace(
    '<img id="bg" ',
    '<img id="bg2" data-lp-type="image" data-fit="cover" data-nat="1200x800" src="a.png"\n'
    '       style="left:0;top:0;width:1280px;height:720px">\n  <img id="bg" ')
two = two.replace("#bg {", "#bg2 { left: 0 !important; top: 0 !important; "
                           "width: 320px !important; height: 900px !important; }\n#bg {")
rc, err, out = run(two)
assert rc == 0, err
els, names = elements(out)
imgs = [e for e in els if e["type"] == "lp-pom-image"]
assert len(imgs) == 2
assert imgs[0]["content"]["asset"]["uuid"] == imgs[1]["content"]["asset"]["uuid"]
assert sum(1 for n in names if "/assets/" in n and n.endswith("a.png")) == 1, names

# ---- geometry.py: snap maths + height write-back -------------------------------
import geometry as G
assert G.nearest("left", 73, "desktop") == 70
assert G.nearest("top", 99, "desktop") == 96
assert G.nearest("width", 276, "mobile") == 300
assert 10 in G.lefts("mobile") and 62 in G.lefts("mobile")
assert G.spans("desktop")[-1] == 1140 and G.spans("mobile")[-1] == 300
H = '<div style="left:70px;height:44px" id="x" data-lp-type="text"></div>'
h2, old = G.set_inline_height(H, "x", 22)
assert old == 44 and "height:22px" in h2, h2
M = "@media (max-width:600px){\n#x { left: 10px !important; height: 44px !important; }\n}"
m2, old = G.set_media_height(M, "x", 22)
assert old == 44 and "height: 22px !important" in m2, m2
_, old = G.set_media_height("#x { display: none !important; }", "x", 22)
assert old is None                     # no height in the rule -> skipped, never invented

shutil.rmtree(os.path.dirname(out), ignore_errors=True)
print("test_transcribe: PASS")
