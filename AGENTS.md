## Dreamliner

This project has a Dreamliner knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `$dreamliner`, use the installed Dreamliner skill or instructions before doing anything else.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure when you need a broad overview. Prefer `dreamliner query "<question>"` when graphify-out/graph.json exists.
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files.
- After modifying code files in this session, run `dreamliner update .` to keep the graph current (AST-only, no API cost).
- This repository is a Codex-only Dreamliner variant. Do not install or document Claude Code, Cursor, or Gemini CLI as first-class hosts.
