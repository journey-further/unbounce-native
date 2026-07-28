# Connected mode uses a fork of the Unbounce MCP, not code vendored into this repo

The connected capabilities (upload, read-back, in-place update) come from the third-party
Unbounce MCP, consumed as a **JF-maintained GitHub fork** that adds the
`get_variant_elements` / `set_variant_elements` pair, with the pair PR'd upstream in
parallel. If the PR merges, the fork is deleted and everyone points back upstream.

Why a fork and not vendoring the ~8 tools we use into the plugin: the upstream repo has no
licence, so copying its code into a different repo is not ours to do — but forking a public
repo on GitHub is expressly permitted by GitHub's terms, which makes the fork the only
self-serve legally clean route. The fork also keeps upstream fixes a rebase away instead of
a manual port, and keeps Playwright plus a reverse-engineered API surface (edit.json,
save.xml, presigned S3, GraphQL) out of a repo whose transcriber is deliberately
dependency-free. The 44-vs-8 tool count costs nothing in practice (schemas are deferred).

The self-contained install experience is achieved without vendoring: the plugin manifest
references the fork as its MCP server, so the client installs one thing. Vendoring proper
stays a nice-to-have, unlocked only if the author grants a licence (worth asking in the PR)
or upstream goes unmaintained.
