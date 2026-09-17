# graphify reference: commit hook and native AGENTS.md integration

Load this when the user asked to install the post-commit hook or wire graphify into a project's AGENTS.md.

## For git commit hook

Install a post-commit hook that auto-rebuilds the graph after every commit. No background process needed - triggers once per commit, works with any editor.

```bash
graphify hook install    # install
graphify hook uninstall  # remove
graphify hook status     # check
```

After every `git commit`, the hook detects which code files changed (via `git diff HEAD~1`), re-runs AST extraction on those files, and rebuilds `graph.json` and `GRAPH_REPORT.md`. Doc/image changes are ignored by the hook - run `$dreamliner --update` manually for those.

If a post-commit hook already exists, graphify appends to it rather than replacing it.

---

## For native AGENTS.md integration (Dreamliner / Codex)

Run once per project to make graphify always-on in Codex sessions:

```bash
graphify install --platform codex
graphify install --project
```

This writes a `## graphify` section to the local `AGENTS.md` that instructs Codex to check the graph before answering codebase questions and rebuild it after code changes. No manual `$dreamliner` needed in future sessions.

> **Dreamliner / Codex:** always-on guidance lives in `AGENTS.md`. The `.codex/hooks.json` PreToolUse entry is an intentional no-op (Codex Desktop rejects additionalContext). Invoke the skill as `$dreamliner`.

```bash
graphify uninstall --project --platform codex
```
