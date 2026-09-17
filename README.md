# Dreamliner

**Codex-only knowledge graphs.** Dreamliner is a Codex variant of [Graphify](https://github.com/Graphify-Labs/graphify): local deterministic AST parsing into a queryable knowledge graph. Every edge is explained. There is no vector store.

This fork targets **OpenAI Codex only**. Claude Code, Cursor, Gemini CLI, and other agent hosts are not first-class here — use upstream Graphify for those.

Type `$dreamliner` in Codex and it maps your project (code, docs, PDFs, images, videos) into a graph you can **query instead of grepping**.

- **Code maps for free, fully local.** Tree-sitter AST: deterministic, no LLM, nothing leaves your machine. (Docs, PDFs, images and video use the Codex session, or a configured API key, for a semantic pass.)
- **Every edge is explained.** Each connection is tagged `EXTRACTED` (explicit in the source) or `INFERRED` (resolved by the engine), so you can tell what was read directly from what was inferred.
- **Not a vector index.** No embeddings, no vector store: a real graph you traverse.

The Python import package remains `graphify` and graphs still write to `graphify-out/` so existing graphs and scripts keep working. The product, skill, and CLI you type are **Dreamliner**.

---

## Get started (Codex)

### Clean machine (copy-paste)

On a machine that has only Python 3.10+ and a shell:

```bash
# 1. Install OpenAI Codex and confirm the binary exists
#    https://openai.com/codex/
codex --version

# 2. Enable parallel extraction (required for $dreamliner on docs/papers/images)
mkdir -p ~/.codex
cat >> ~/.codex/config.toml <<'EOF'
[features]
multi_agent = true
EOF

# 3. Install Dreamliner from this fork
uv tool install git+https://github.com/KRNichols/graphify.git@cursor/dreamliner-codex-rebrand-5833
# or from a clone:
#   git clone https://github.com/KRNichols/graphify && cd graphify && pip install -e .

# 4. Register the Codex skill and verify the machine is ready
dreamliner install                 # user-global: ~/.codex/skills/dreamliner/
dreamliner doctor                  # FAIL items are actionable; fix them before using Codex
```

Restart Codex, then in a project:

```
$dreamliner .
dreamliner query "how does this codebase fit together?"
```

`dreamliner doctor --graph` also fails if `graphify-out/graph.json` is missing, empty, or corrupt.

### Install only

```bash
uv tool install git+https://github.com/KRNichols/graphify.git@cursor/dreamliner-codex-rebrand-5833
# or from a clone:
pip install -e .

dreamliner install                 # user-global: ~/.codex/skills/dreamliner/
# or:
dreamliner install --project       # repo-local: ./.codex/skills/dreamliner/
```

Enable parallel extraction in `~/.codex/config.toml`:

```toml
[features]
multi_agent = true
```

Restart Codex, then:

```
$dreamliner .
```

That writes three files:

```
graphify-out/
├── graph.html       open in any browser — click nodes, filter, search
├── GRAPH_REPORT.md  key concepts, surprising connections, suggested questions
└── graph.json       the full graph — query it without re-reading your files
```

`dreamliner` and `graphify` are the same CLI (`graphify` is a compatibility alias).

---

## Try it

```text
$ dreamliner explain "APIRouter"
Node: APIRouter
  Source:    routing.py L2210
  Community: 2
  Degree:    47

$ dreamliner path "FastAPI" "ModelField"
Shortest path (3 hops):
  FastAPI --uses--> DefaultPlaceholder <--references-- get_request_handler() --references--> ModelField

$ dreamliner query "how does routing work?"
```

Every edge carries a confidence tag (`EXTRACTED` = explicit in the source, `INFERRED` = derived). `dreamliner query` returns a scoped subgraph; `dreamliner path A B` traces how two things connect.

---

## What it does

| Capability | What you get |
|---|---|
| **God nodes** | The most-connected concepts |
| **Communities** | Subsystems (Leiden), labeled without an LLM |
| **Cross-file links** | `calls` / `imports` / `inherits` resolved across ~40 languages via tree-sitter |
| **Query, path, explain** | Ask a question, trace a path, or explain one concept against `graph.json` |
| **Local-first** | Code is parsed locally; only the optional semantic pass over docs/media calls a model |

More detail: [docs/how-it-works.md](./docs/how-it-works.md). Benchmarks vs other systems: [BENCHMARKS.md](./BENCHMARKS.md).

---

## Prerequisites

| Requirement | Minimum | Install |
|---|---|---|
| Python | 3.10+ | [python.org](https://www.python.org/downloads/) |
| uv *(recommended)* | any | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Codex | current | [OpenAI Codex](https://openai.com/codex/) |

---

## Always-on in a repo

```bash
dreamliner install --project
```

This writes:

- `.codex/skills/dreamliner/SKILL.md` plus `references/`
- a `## Dreamliner` section in `AGENTS.md`
- a no-op Codex `PreToolUse` hook in `.codex/hooks.json` (Codex Desktop rejects `additionalContext` on that hook; AGENTS.md is the real always-on path)

Codex then prefers `dreamliner query "<question>"` over grepping raw files.

Remove it with `dreamliner uninstall` (add `--purge` to delete `graphify-out/`).

---

## Common commands

```bash
$dreamliner .                        # build graph for current folder
$dreamliner ./docs --update          # re-extract only changed files
$dreamliner . --cluster-only         # rerun clustering without re-extracting
dreamliner query "what connects auth to the database?"
dreamliner path "UserService" "DatabasePool"
dreamliner explain "RateLimiter"
dreamliner hook install              # auto-rebuild on commit + branch checkout
```

Headless (no Codex skill):

```bash
dreamliner extract .                 # local AST for code; optional LLM for docs
dreamliner update .
dreamliner query "show the auth flow"
```

---

## Troubleshooting

**`dreamliner: command not found`**
The CLI is installed but not on `PATH`. After `uv tool install`, run `uv tool update-shell` and open a new terminal. `python -m graphify` also works.

**`Codex CLI not found`**
`codex` is not on `PATH`. Install [OpenAI Codex](https://openai.com/codex/), open a new terminal, then `dreamliner doctor`.

**`Codex config ... is missing or does not enable multi-agent`**
Add `multi_agent = true` under `[features]` in `~/.codex/config.toml` (or `$CODEX_HOME/config.toml`). Invalid TOML is also a hard failure.

**Codex does not list `$dreamliner`**
Run `dreamliner install`, confirm `~/.codex/skills/dreamliner/SKILL.md` (or the project path) exists, and restart Codex.

**`spawn_agent` is unavailable**
Add `multi_agent = true` under `[features]` in `~/.codex/config.toml` and restart Codex. A code-only corpus can still build (AST only).

**`no Dreamliner graph found`**
There is no `graphify-out/graph.json` yet. Run `$dreamliner .` or `dreamliner extract .`.

**Empty graph**
The extract produced no nodes. Check the path, ignore rules (`.gitignore` / `.graphifyignore`), and that the folder has supported files.

**`Dreamliner could not load graph`**
`graph.json` is truncated or invalid JSON. Rebuild with `$dreamliner . --force` or `dreamliner extract . --force`.

**This is not Claude Code / Cursor / Gemini CLI**
Those hosts are not supported in this variant. Use [upstream Graphify](https://github.com/Graphify-Labs/graphify).

---

## Privacy

- **Code files** — processed locally via tree-sitter. Nothing leaves your machine.
- **Docs, PDFs, images** — sent through the Codex session (or a configured backend) for semantic extraction.
- **No telemetry**, no usage tracking, no analytics.

---

## License

Apache-2.0. This is a branded Codex-only fork of Graphify; the graph engine is unchanged.
