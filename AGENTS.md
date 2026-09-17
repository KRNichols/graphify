## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)
- Extraction JSON is gated by Dreamliner Check (`validate_extraction` / `assert_valid` in graphify/validate.py). Bad payloads fail closed. Do not delete or weaken that function.
