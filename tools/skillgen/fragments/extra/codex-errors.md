## Codex clean-machine failures

If a bash block fails with `command not found`, `ModuleNotFoundError`, or an empty graph, **stop**. Do not retry the same one-liner. Run:

```
graphify check
```

(`graphify check --project` after a project-scoped install.) Print the `error:` / `next:` block to the user. Typical failures:

1. **Missing Python / uv / pipx / `graphify` not on PATH** — install Python 3.10+, then `uv tool install graphifyy` (or `pipx install graphifyy`) and put `~/.local/bin` on PATH (`uv tool update-shell` / `pipx ensurepath`).
2. **Missing or broken `~/.codex/config.toml`** — create or fix the file. Parallel extraction via `spawn_agent` needs `[features]` `multi_agent = true`, then restart Codex.
3. **Skill installed outside `~/.codex/` or `./.codex/`** — Codex will not load `~/.claude/skills/...`. Re-run `graphify install --platform codex` or `graphify install --project --platform codex`.
4. **Stale `graphify-out/.graphify_python`** — this sidecar is the interpreter for every later bash block. If it is missing, empty, or points at a python that cannot `import graphify`, delete it and re-run `$graphify`. A raw `ModuleNotFoundError` is this contract failing, not a missing extra.
5. **Empty / missing `graphify-out/graph.json`** — do not label or visualize. Re-run `graphify extract .` from the project root (or `$graphify .`). If detect found 0 files, the path or ignore rules are wrong.

Never emit Claude-style `hookSpecificOutput` / `additionalContext` JSON. Codex Desktop rejects that on PreToolUse; the installed hook is `graphify hook-check` (silent no-op, exit 0). Graph guidance comes from AGENTS.md.

---
