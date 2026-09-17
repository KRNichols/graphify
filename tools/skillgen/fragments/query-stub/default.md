When `graphify-out/graph.json` already exists and the user asks a question about the corpus, answer from the graph rather than rebuilding it:

```bash
dreamliner query "<question>"
```

If that command fails (missing binary, missing graph, empty graph, or unreadable JSON), stop and show the CLI error. Do not invent an answer from memory.

Before traversal, expand the question against the graph's own vocabulary so a wording mismatch does not collapse the answer to noise. If the `dreamliner query` CLI is unavailable, fall back to an inline NetworkX traversal of `graphify-out/graph.json` only after confirming the file exists and parses. Answer using only what the graph output contains, and quote `source_location` when citing a specific fact. For that vocab-expansion step, the BFS/DFS traversal modes, the `--budget` cap, the NetworkX fallback, `save-result` feedback, and the `$dreamliner path` and `$dreamliner explain` flows, see `references/query.md`.
