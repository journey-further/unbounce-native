---
name: build-page
description: Turn a measured design.html into an importable .unbounce archive of native elements
argument-hint: [path to design.html or its folder, and the page name]
---

Invoke the `build-page` skill and follow it. Read its `SKILL.md` before you do anything else.

If the user gave no page name, ask for one before you build. The name inside the file wins over
the name given at upload, so this is the only place to set it.

$ARGUMENTS
