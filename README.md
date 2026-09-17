# Dreamliner

**Codex-only** knowledge graph for a folder of code, docs, papers, images, or video. Type `$dreamliner` in Codex and you get a persistent graph you can **query instead of grepping**.

Dreamliner is a Codex-only rebrand of [Graphify](https://github.com/Graphify-Labs/graphify). The Python import path is still `graphify` and on-disk output is still `graphify-out/` (see leftover note below). User-facing CLI, skill, and docs are Dreamliner.

- **Code maps for free, fully local.** Tree-sitter AST: deterministic, no LLM, nothing leaves your machine.
- **Docs/media use Codex.** Semantic extraction (docs, PDFs, images, video) uses the Codex session (`spawn_agent`). Gemini/Claude are not first-class hosts on this variant.
- **Every edge is explained.** `EXTRACTED` (in the source) or `INFERRED` (resolved), so you can tell what was read from what was derived.
- **Validation still runs.** `validate_extraction` / `assert_valid` in `graphify/validate.py` still check extraction JSON. The CLI surface is `dreamliner validate`.

```
graphify-out/
├── graph.html       open in any browser
├── GRAPH_REPORT.md  god nodes, surprising connections, suggested questions
└── graph.json       query / path / explain without re-reading files
```

---

## How to run Dreamliner with Codex on a clean machine

Requirements: **Python 3.10+**, **[uv](https://docs.astral.sh/uv/)**, **[Codex](https://github.com/openai/codex)**.

```bash
# 1. Python
python3 --version    # 3.10 or newer

# 2. uv (recommended installer)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version

# 3. Codex CLI — must be on PATH
codex --version
# If this fails: install Codex, open a new shell, retry.

# 4. Enable Codex multi-agent (required for spawn_agent)
mkdir -p ~/.codex
cat >> ~/.codex/config.toml <<'EOF'
[features]
multi_agent = true
EOF
# Restart Codex after editing config.toml.

# 5. Install the package (PyPI name is still graphifyy)
uv tool install graphifyy
uv tool update-shell    # if `dreamliner` is not found, then open a new terminal

# 6. Register the Codex skill + AGENTS.md always-on
dreamliner install
# same as: dreamliner install --platform codex
#      or: dreamliner codex install
# project-scoped: dreamliner install --project

# 7. Check the machine
dreamliner doctor
```

Then in Codex, from the repo root:

```
$dreamliner .
```

That builds the graph (AST for code; Codex for docs if any). After it finishes:

```
$dreamliner query "how does install work?"
$dreamliner path "install" "validate_extraction"
$dreamliner explain "Dreamliner"
```

Or from a shell:

```bash
dreamliner query "how does install work?"
dreamliner path "install" "validate_extraction"
dreamliner explain "Dreamliner"
dreamliner validate                  # schema checks (validate_extraction / assert_valid)
```

Empty or failed graphs print an actionable error (rebuild with `$dreamliner .`), not a traceback. Missing Codex CLI or a `~/.codex/config.toml` without `multi_agent = true` under `[features]` is the same: a clear fix, not a stack trace.

The Codex PreToolUse hook is an **intentional no-op**. Always-on guidance is **AGENTS.md**. Do not emit `hookSpecificOutput.additionalContext` on PreToolUse — Codex Desktop rejects it and it breaks Bash.

---

## Get started (already have Python / uv / Codex)

```bash
uv tool install graphifyy
dreamliner install
```

In Codex:

```
$dreamliner .
```

---

## Always-on in Codex

`dreamliner install` (or `dreamliner codex install`) writes:

- `~/.codex/skills/dreamliner/SKILL.md` (and `references/`)
- a `## Dreamliner` section in the project's `AGENTS.md`
- `.codex/hooks.json` PreToolUse → `dreamliner hook-check` (no-op)

Claude Code, Cursor, Gemini CLI, and other multi-host installers are **not first-class**. `dreamliner claude install`, `dreamliner cursor install`, `dreamliner gemini install`, and `--platform claude` exit with an error pointing you back to Codex.

---

## Query, path, explain

Once `graphify-out/graph.json` exists:

```text
$ dreamliner explain "APIRouter"
Node: APIRouter
  Source:    routing.py L2210
  Community: 2
  Degree:    47

$ dreamliner path "FastAPI" "ModelField"
Shortest path (3 hops):
  FastAPI --uses--> DefaultPlaceholder <--references-- get_request_handler() --references--> ModelField
```

`dreamliner query "<question>"` returns a scoped subgraph. After code changes, `dreamliner update .` refreshes the graph with AST only (no API cost).

---

## Validation (not a separate "verify" product)

Dreamliner validation is the existing extraction schema check:

- Library: `graphify.validate.validate_extraction` / `assert_valid` (unchanged)
- CLI: `dreamliner validate [file]` (default `graphify-out/graph.json`)
- The skill's graph-health step still runs during `$dreamliner .`

There is no product-level `verify` command. Use `dreamliner validate`.

---

## What it does

| Capability | What you get |
|---|---|
| **God nodes** | Most-connected concepts |
| **Communities** | Leiden subsystems, LLM-free labels |
| **Cross-file links** | `calls` / `imports` / `inherits` across ~40 languages via tree-sitter |
| **Query, path, explain** | Ask, trace, or explain against `graph.json` |
| **Local-first code** | AST only; no LLM for code |

Code is extracted locally. Semantic/LLM backends that assumed Claude or Gemini as the default host are demoted: Codex is the happy path.

---

## Prerequisites

| Requirement | Minimum | Check |
|---|---|---|
| Python | 3.10+ | `python3 --version` |
| uv | any | `uv --version` |
| Codex | current | `codex --version` |
| Codex config | `[features] multi_agent = true` | `dreamliner doctor` |

**macOS:** `brew install python@3.12` then install uv and Codex.  
**Windows:** `winget install astral-sh.uv` then install Codex.  
**Ubuntu/Debian:** `sudo apt install python3.12` then install uv and Codex.

The PyPI package is still **`graphifyy`** (double-y). The user-facing command is **`dreamliner`**. `graphify` remains as a compatibility alias for the same CLI.

If `dreamliner` is not found after `uv tool install`, run `uv tool update-shell` and open a new terminal. With `uvx`: `uvx --from graphifyy dreamliner install`.

---

## Optional extras

Same extras as upstream Graphify (`pdf`, `office`, `video`, `mcp`, `leiden`, …):

```bash
uv tool install "graphifyy[pdf]"
```

Gemini/Anthropic extras exist for headless `dreamliner extract --backend …` only. They are not the install host.

---

## Common commands

```bash
$dreamliner .                        # build graph for current folder
$dreamliner ./docs --update          # re-extract only changed files
dreamliner query "what connects auth to the database?"
dreamliner path "UserService" "DatabasePool"
dreamliner explain "RateLimiter"
dreamliner validate
dreamliner doctor
dreamliner update .                  # AST-only refresh after code changes
dreamliner extract . --code-only     # headless AST extract (CI)
```

Uninstall: `dreamliner uninstall` (add `--purge` to delete `graphify-out/`).

---

## Leftover internal names

This pass does **not** rename the Python package. You will still see:

| Surface | Name | Why |
|---|---|---|
| PyPI | `graphifyy` | Existing package; full rename is a separate publish |
| Import | `import graphify` | AST extractors, tests, and `validate.py` stay stable |
| Output dir | `graphify-out/` | Existing graphs keep working |
| Compatibility CLI | `graphify` | Same entry point as `dreamliner` |

User-facing skill invoke, install UX, AGENTS.md, and README use **Dreamliner** / `$dreamliner` / `dreamliner`.

---

## License

Apache-2.0. See `LICENSE`, `LICENSE-MIT`, and `NOTICE`.
