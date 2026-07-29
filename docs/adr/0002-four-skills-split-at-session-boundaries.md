# Four skills, split at session boundaries, with files on disk as the contract

The single `design-page` skill splits into `design-page` (brief → approved design HTML;
iterative, gated, multi-session), `build-page` (design HTML → `.unbounce`; run-once,
mechanical), `upload-page` (`.unbounce` → page in the account; run-once, connected-only,
never publishes) and `edit-page` (live page → same page updated in place; connected-only,
always starts from a fresh element read).

The seams are session boundaries, not conceptual tidiness: a design must be resumable across
sessions ("pick up Tuesday's design and keep tweaking"), which forces every skill to work
from files in the working folder rather than conversation state — the same discipline that
makes a cold-start test meaningful. It also removes the need to run design → build → upload
end to end with one agent in one session.

Connected capability arrives as whole skills that don't function without the MCP tools; no
skill ever branches on "am I connected?". There is deliberately no separate upload *step*
inside build and no design/build gate inside one skill — those were the rejected
alternatives (one long skill with pause points, or a two-way design/build split without the
connected skills).
