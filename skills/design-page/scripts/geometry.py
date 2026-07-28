#!/usr/bin/env python3
"""Design-time geometry helper — the mechanical half of the measure loop.

    python3 geometry.py tables                        # legal lefts + spans, both breakpoints
    python3 geometry.py snap left 73 desktop          # -> nearest legal value
    python3 geometry.py heights design.html desktop.json [mobile.json] [--write]

`heights` diffs every text element's declared height against measure.mjs output and, with
--write, patches the measured values back — inline styles for desktop reports, the @media
block for mobile reports. Text heights only: section heights and stacking are design
decisions, not measurements (SKILL.md step 3).

⚠️ Measured heights inherit measure.mjs's known caveats (the <p> strut floor — see
BACKLOG.md) — this tool applies what was measured, it doesn't judge it.

Stdlib only, same as transcribe.py.
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# BP lives with the transcriber (build-page) and is single-source on purpose: a duplicated
# grid constant that drifts hands out "legal" values the transcriber then rejects.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "build-page", "scripts"))
from transcribe import BP


def lefts(bp):
    """Legal left positions: {pad + k·pitch} ∪ {pad + k·pitch + colW}."""
    cfg = BP[bp]
    out, k = set(), 0
    while cfg["pad"] + k * cfg["pitch"] <= cfg["canvas"]:
        out.add(cfg["pad"] + k * cfg["pitch"])
        out.add(cfg["pad"] + k * cfg["pitch"] + cfg["colw"])
        k += 1
    return sorted(v for v in out if v <= cfg["canvas"])


def spans(bp):
    """Whole spans: pitch·n − 12, up to the content width."""
    cfg = BP[bp]
    return [cfg["pitch"] * n - 12 for n in range(1, cfg["cols"] + 1)
            if cfg["pitch"] * n - 12 <= cfg["canvas"] - 2 * cfg["pad"]]


def nearest(kind, v, bp):
    cfg = BP[bp]
    if kind == "top":
        return int(round(v / cfg["rh"]) * cfg["rh"])
    cands = {"left": lefts, "width": spans}.get(kind)
    if not cands:
        raise SystemExit(f"unknown kind {kind!r} (left|top|width)")
    return min(cands(bp), key=lambda c: abs(c - v))


def set_inline_height(html, eid, h):
    """Set height:...px inside the style attribute of the tag carrying id=eid.
    Returns (html, previous value or None). Matches the whole tag first, so attribute
    order can't break it (bakeoff arm a's regex failure mode)."""
    old = [None]

    def fix(m):
        def sub(x):
            old[0] = float(x.group(2))
            return f"{x.group(1)}{h:g}{x.group(3)}"
        return re.sub(r"(height:\s*)([\d.]+)(px)", sub, m.group(0), count=1)

    html = re.sub(r'<[^>]*\bid="%s"[^>]*>' % re.escape(eid), fix, html, count=1)
    return html, old[0]


def set_media_height(html, eid, h):
    """Set the height in #eid's @media rule. Returns (html, previous value or None) —
    None when the element has no rule or no height (e.g. display:none), which is skipped,
    never invented."""
    old = [None]

    def sub(m):
        old[0] = float(m.group(2))
        return f"{m.group(1)}{h:g}{m.group(3)}"

    html = re.sub(r"(#%s\s*\{[^}]*?height:\s*)([\d.]+)(px\s*!important)" % re.escape(eid),
                  sub, html, count=1)
    return html, old[0]


def heights(design, reports, write):
    html = open(design).read()
    changes = 0
    for path in reports:
        rep = json.load(open(path))
        bp = rep.get("breakpoint", "desktop")
        setter = set_media_height if bp == "mobile" else set_inline_height
        for eid, h in sorted(rep.get("text", {}).items()):
            html, old = setter(html, eid, h)
            if old is None or old == h:
                continue
            changes += 1
            print(f"#{eid} [{bp}]: {old:g} -> {h:g}")
    if not changes:
        print("all declared text heights already match measured")
        return
    if write:
        open(design, "w").write(html)
        print(f"{changes} change(s) written to {design} — re-run measure.mjs to confirm stable")
    else:
        print(f"{changes} change(s) (dry run — pass --write to apply)")


def main():
    a = sys.argv[1:]
    if not a or a[0] == "tables":
        for bp in BP:
            print(f"{bp} lefts: {lefts(bp)}")
            print(f"{bp} spans: {spans(bp)}")
    elif a[0] == "snap" and len(a) >= 3:
        print(nearest(a[1], float(a[2]), a[3] if len(a) > 3 else "desktop"))
    elif a[0] == "heights" and len(a) >= 3:
        heights(a[1], [x for x in a[2:] if x != "--write"], "--write" in a)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
