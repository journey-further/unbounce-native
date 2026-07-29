#!/usr/bin/env python3
"""Diff two Unbounce element arrays; non-zero exit on real drift.

Usage:
    diff_elements.py A.json B.json             # strict — for read → write → re-read
    diff_elements.py --import A.json B.json    # across an upload — ignores what import rewrites
    diff_elements.py --selftest

Each input is either a bare JSON array of elements or an object with an
"elements" key (both shapes come out of the MCP tools and transcribe.py).

Strict mode compares everything except numeric *type*: import coerces `70.0`
to `70` (P3, 2026-07-29), so numbers are compared by value, never by type.
`--import` additionally ignores the only keys import legitimately rewrites —
`content.asset.{uuid,content_url,unique_url}` changed and `content.asset.id`
added (the whole P3 list). Element ids and timestamps are NOT rewritten by
import, so they are always compared.

A clean diff is necessary but never sufficient: P4 proved a byte-identical
array can sit on a blank page. Screenshot after every write regardless.
"""

import json
import sys

IMPORT_REWRITTEN = {"content.asset.uuid", "content.asset.content_url",
                    "content.asset.unique_url", "content.asset.id"}


def load(path):
    with open(path) as f:
        data = json.load(f)
    return data if isinstance(data, list) else data["elements"]


def is_number(v):
    # bool is an int subclass; True == 1 must still count as drift
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def walk(a, b, path, out):
    if is_number(a) and is_number(b):
        if a != b:
            out.append((path, a, b))
    elif type(a) is not type(b):
        out.append((path, a, b))
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            p = f"{path}.{k}" if path else k
            if k not in a:
                out.append((p, "<absent>", b[k]))
            elif k not in b:
                out.append((p, a[k], "<absent>"))
            else:
                walk(a[k], b[k], p, out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append((f"{path}[len]", len(a), len(b)))
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, f"{path}[{i}]", out)
    elif a != b:
        out.append((path, a, b))


def diff(elements_a, elements_b, import_mode=False):
    """Return a list of (element_id, key_path, a, b) drift entries."""
    by_id_a = {e["id"]: e for e in elements_a}
    by_id_b = {e["id"]: e for e in elements_b}
    drift = []
    for eid in sorted(set(by_id_a) - set(by_id_b)):
        drift.append((eid, "<element>", "present", "<absent>"))
    for eid in sorted(set(by_id_b) - set(by_id_a)):
        drift.append((eid, "<element>", "<absent>", "present"))
    for eid in sorted(set(by_id_a) & set(by_id_b)):
        fields = []
        walk(by_id_a[eid], by_id_b[eid], "", fields)
        for path, a, b in fields:
            # strip list indices so content.asset keys match whatever nesting they sit at
            bare = path.split("[")[0]
            if import_mode and any(bare.endswith(k) for k in IMPORT_REWRITTEN):
                continue
            drift.append((eid, path, a, b))
    return drift


def clip(v):
    s = json.dumps(v) if not isinstance(v, str) else v
    return s[:80] + "…" if len(s) > 80 else s


def main(argv):
    import_mode = "--import" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if len(paths) != 2:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    drift = diff(load(paths[0]), load(paths[1]), import_mode)
    if not drift:
        print(f"OK  no drift across {len(load(paths[0]))} elements"
              f"{' (import-rewritten asset keys ignored)' if import_mode else ''}")
        return 0
    print(f"DRIFT  {len(drift)} differences:")
    for eid, path, a, b in drift[:50]:
        print(f"  {eid} {path}: {clip(a)}  ->  {clip(b)}")
    if len(drift) > 50:
        print(f"  … and {len(drift) - 50} more")
    return 1


def selftest():
    base = [{"id": "lp-pom-root", "type": "lp-pom-root",
             "geometry": {"offset": {"left": 70.0, "top": 12}},
             "content": {"asset": {"uuid": "aaa", "content_url": "/a", "unique_url": "/a2"},
                         "text": "hello"}}]
    same_by_value = json.loads(json.dumps(base).replace("70.0", "70"))
    assert diff(base, same_by_value) == [], "float->int coercion is not drift"

    imported = json.loads(json.dumps(base))
    imported[0]["content"]["asset"] = {"uuid": "bbb", "content_url": "/b",
                                       "unique_url": "/b2", "id": 123}
    assert len(diff(base, imported)) == 4, "strict mode sees asset rewrites"
    assert diff(base, imported, import_mode=True) == [], "--import ignores them"

    edited = json.loads(json.dumps(base))
    edited[0]["content"]["text"] = "changed"
    edited[0]["customClassnames"] = ["oops-an-array"]
    d = diff(base, edited, import_mode=True)
    assert ("lp-pom-root", "content.text", "hello", "changed") in d
    assert any(p == "customClassnames" for _, p, _, _ in d), "added keys are drift"

    dropped = []
    assert diff(base, dropped) == [("lp-pom-root", "<element>", "present", "<absent>")]

    bool_drift = json.loads(json.dumps(base))
    bool_drift[0]["geometry"]["offset"]["top"] = True  # True == 1 must not hide as a number
    assert any(p == "geometry.offset.top" for _, p, _, _ in diff(
        [{**base[0], "geometry": {"offset": {"left": 70, "top": 1}}}], bool_drift))

    print("diff_elements selftest: PASS")


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main(sys.argv[1:]))
