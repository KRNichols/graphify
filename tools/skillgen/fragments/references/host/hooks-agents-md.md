# Dreamliner reference: commit hook and native AGENTS.md integration

Load this when the user asked to install the post-commit hook or wire Dreamliner into a project's AGENTS.md.

## For git commit hook

Install a post-commit hook that auto-rebuilds the graph after every commit. No background process needed - triggers once per commit, works with any editor.

```bash
dreamliner hook install    # install
dreamliner hook uninstall  # remove
dreamliner hook status     # check
```

After every `git commit`, the hook detects which code files changed (via `git diff HEAD~1`), re-runs AST extraction on those files, and rebuilds `graph.json` and `GRAPH_REPORT.md`. Doc/image changes are ignored by the hook - run `$dreamliner --update` manually for those.

If a post-commit hook already exists, Dreamliner appends to it rather than replacing it.

---

## For native AGENTS.md integration@@AGENTS_HEADING_SUFFIX@@

Run once per project to make Dreamliner always-on in @@HOST_DISPLAY@@ sessions:

```bash
@@AGENTS_INSTALL_BLOCK@@
```

This writes a `## Dreamliner` section to the local `AGENTS.md` that instructs @@HOST_DISPLAY@@ to check the graph before answering codebase questions and rebuild it after code changes. No manual `$dreamliner` needed in future sessions.
@@AGENTS_PRETOOLUSE_NOTE@@
```bash
@@AGENTS_UNINSTALL_BLOCK@@
```
