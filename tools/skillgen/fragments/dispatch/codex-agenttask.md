**Step B2 - Dispatch ALL subagents in a single message (Codex)**

> **Codex:** Uses `spawn_agent` + `wait_agent` + `close_agent`.
> Requires `multi_agent = true` under `[features]` in `~/.codex/config.toml`.
> If `spawn_agent` is unavailable, do **not** silently skip semantic extraction.
> Tell the user: add `multi_agent = true` under `[features]` in `~/.codex/config.toml`, restart Codex, and retry.
> A code-only corpus can continue without subagents (AST only) — write the empty semantic file and go to Part C.

Call `spawn_agent` once per chunk — ALL in the same response so they run in parallel. Build the message by wrapping the extraction prompt in task-delegation framing:

```
spawn_agent(agent_type="worker", message="Your task is to perform the following. Follow the instructions below exactly.\n\n<agent-instructions>\n[extraction prompt, with FILE_LIST, CHUNK_NUM, TOTAL_CHUNKS, DEEP_MODE substituted]\n</agent-instructions>\n\nExecute this now. Output ONLY the structured JSON response.")
```

After all agents are dispatched, collect results sequentially in memory:
```
result = wait_agent(handle); close_agent(handle)   # repeat per handle
```

Parse each result as JSON. If a result is not valid JSON with `nodes` and `edges`, print a warning naming the chunk and skip it — do not abort unless more than half the chunks fail. Accumulate nodes/edges/hyperedges across valid results and write to `graphify-out/.graphify_semantic_new.json`. Codex collects in memory, so there are no per-chunk files on disk; the disk-based success checks in Step B3 do not apply — a chunk that returns invalid JSON is the failure signal instead.

Subagent prompt template:

See `references/extraction-spec.md` for the compact subagent prompt (rules, node-ID format, confidence rubric, hyperedge and vision rules, JSON schema). Load it only here, only when at least one chunk holds a doc, paper, or image; a pure-code corpus has skipped Part B and never reads it. Pass each agent that prompt verbatim with FILE_LIST, CHUNK_NUM, TOTAL_CHUNKS, and DEEP_MODE substituted, and have it return the JSON inline.
