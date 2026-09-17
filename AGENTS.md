## Dreamliner

This project has a Dreamliner knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `$dreamliner`, use the installed Dreamliner skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `dreamliner query "<question>"` when graphify-out/graph.json exists. Use `dreamliner path "<A>" "<B>"` for relationships and `dreamliner explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip Dreamliner. Only skip Dreamliner if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `dreamliner update .` to keep the graph current (AST-only, no API cost).

Internal leftover: the Python package import path is still `graphify` and on-disk output is `graphify-out/`. After modifying code files, `graphify update .` (AST-only) is the same rebuild as `dreamliner update .`.
