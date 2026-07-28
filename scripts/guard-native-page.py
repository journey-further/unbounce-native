#!/usr/bin/env python3
"""PreToolUse guard: the two MCP tools that flatten a native Unbounce page.

`deploy_page` and `edit_variant` both assume a page IS an lp-code blob. On a page
built by this plugin that assumption is false and the damage is silent:

  deploy_page  — packages the whole body into one lp-code element, which is the
                 exact failure this plugin exists to prevent.
  edit_variant — writes into the FIRST lp-code element it finds. On a native page
                 that is usually a small widget or an inline SVG icon, so the edit
                 lands on decoration, the copy you meant to change is untouched,
                 and the icon is replaced by a page.

Both are legitimate on an MCP-managed page (one the agent authored as HTML/CSS),
so this is `ask`, not `deny` — a human decides which kind of page is being
targeted, because the tool input alone does not say. What the guard removes is
the possibility of destroying a client's page without anyone being asked.

Wired up by hooks/hooks.json. Matched by tool-name suffix across any server name,
so it holds whether the MCP came from this plugin or from `claude mcp add`.
"""

import json
import sys

# Keyed by the bare tool name — the matcher may deliver it under any server
# prefix (`mcp__unbounce__…`, `mcp__plugin_unbounce-native_unbounce__…`).
GUARDED = {
    "deploy_page": (
        "deploy_page packages the entire page body into ONE lp-code element. If this page "
        "was built by unbounce-native, that destroys every native lp-pom-* element and the "
        "client can no longer edit anything in the drag-and-drop editor — the single failure "
        "this plugin exists to prevent. To change a native page, rebuild it with design-page "
        "and build-page, then upload it with upload-page. Only allow this if the target is an "
        "MCP-managed HTML/CSS page."
    ),
    "edit_variant": (
        "edit_variant overwrites the FIRST lp-code element in the variant. On a native "
        "lp-pom-* page that is typically a small widget or an inline SVG icon, so this "
        "replaces a piece of decoration with a whole page and leaves the content you meant "
        "to edit untouched. Read the page with get_variant_elements instead. Only allow this "
        "if the target is an MCP-managed HTML/CSS page."
    ),
}


def decide(tool_name):
    """Return a permissionDecisionReason for a guarded tool, else None.

    Matches on the suffix after the last `__` so any MCP server naming works.
    """
    bare = tool_name.rsplit("__", 1)[-1] if tool_name else ""
    return GUARDED.get(bare)


def main():
    # A guard that crashes must not block real work, so anything unparseable
    # falls through to the normal permission flow rather than failing closed.
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}

    reason = decide(payload.get("tool_name", ""))
    out = {"hookEventName": "PreToolUse"}
    out.update(
        {"permissionDecision": "ask", "permissionDecisionReason": reason}
        if reason
        else {"permissionDecision": "defer"}
    )
    json.dump({"hookSpecificOutput": out}, sys.stdout)


def selftest():
    assert decide("mcp__unbounce__deploy_page")
    assert decide("mcp__plugin_unbounce-native_unbounce__deploy_page")
    assert decide("mcp__unbounce__edit_variant")
    assert decide("mcp__anything__edit_variant"), "server name must not matter"
    assert decide("mcp__unbounce__upload_unbounce_file") is None
    assert decide("mcp__unbounce__get_variant_elements") is None
    assert decide("mcp__unbounce__set_variant_elements") is None, "the native write is allowed"
    assert decide("Bash") is None
    assert decide("") is None
    assert decide(None) is None
    print("guard-native-page selftest: PASS")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
