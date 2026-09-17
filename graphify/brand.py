"""User-facing Dreamliner product names.

Internal Python imports and on-disk graph paths stay ``graphify`` /
``graphify-out`` so existing graphs and ``import graphify`` keep working.
Everything an agent or human types — skill name, slash/dollar command, CLI
entrypoint, AGENTS.md heading — is Dreamliner.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _pkg_version

# Display name (docs, banners, error prefixes).
PRODUCT = "Dreamliner"

# Skill folder + frontmatter ``name`` (Codex invokes this as ``$dreamliner``).
SKILL = "dreamliner"

# User-facing CLI. ``graphify`` remains a compatibility alias.
CLI = "dreamliner"

# Codex skill trigger (Codex uses ``$name``, not ``/name``).
TRIGGER = "$dreamliner"

# AGENTS.md heading written by ``dreamliner install``.
AGENTS_HEADING = "## Dreamliner"

# Legacy heading from the upstream Graphify skill; still stripped on uninstall.
LEGACY_AGENTS_HEADING = "## graphify"

# On-disk graph directory (implementation detail; do not rename).
GRAPH_OUT = "graphify-out"

# Python import package (implementation detail; do not rename).
MODULE = "graphify"

# Distribution names we may be installed as (this fork, or a graphifyy wheel).
_DIST_CANDIDATES = ("dreamliner", "graphifyy")


def package_version() -> str:
    """Return the installed distribution version, or ``unknown``."""
    for name in _DIST_CANDIDATES:
        try:
            return _pkg_version(name)
        except PackageNotFoundError:
            continue
        except Exception:
            continue
    return "unknown"


def missing_graph_message(path: str) -> str:
    """Actionable error when graph.json is absent."""
    return (
        f"error: no {PRODUCT} graph found at {path}. "
        f"Build one first with `{TRIGGER} .` or `{CLI} extract .`."
    )


def empty_graph_message(path: str | None = None) -> str:
    """Actionable error when a graph file exists but has no nodes."""
    where = f" at {path}" if path else ""
    return (
        f"error: {PRODUCT} graph{where} is empty (no nodes). "
        f"Rebuild with `{TRIGGER} .` or `{CLI} extract . --force`. "
        "If the corpus has no supported files, check the path and ignore rules."
    )


def corrupt_graph_message(path: str, exc: BaseException) -> str:
    """Actionable error when graph.json cannot be parsed or loaded."""
    return (
        f"error: {PRODUCT} could not load graph {path}: {exc}. "
        f"The file may be truncated or invalid JSON. Rebuild with `{TRIGGER} . --force` "
        f"or `{CLI} extract . --force`."
    )


def missing_binary_message() -> str:
    """Actionable error when the CLI / import is unavailable."""
    return (
        f"error: {PRODUCT} is not installed in this environment "
        f"(neither `{CLI}` nor `python -m {MODULE}` works). "
        f"Install this fork, then retry:\n"
        f"  uv tool install git+https://github.com/KRNichols/graphify.git@cursor/dreamliner-codex-rebrand-5833\n"
        f"  # or: pipx install git+https://github.com/KRNichols/graphify.git@cursor/dreamliner-codex-rebrand-5833\n"
        f"  # or from a clone: pip install -e .\n"
        f"Then run `{CLI} install` and restart Codex."
    )


def unsupported_host_message(platform: str) -> str:
    """Actionable error when a non-Codex host is requested."""
    return (
        f"error: {PRODUCT} is a Codex-only variant; platform '{platform}' is not supported. "
        f"Install with `{CLI} install` (or `{CLI} install --project`). "
        "For Claude Code, Cursor, Gemini CLI, or other hosts, use upstream Graphify "
        "(https://github.com/Graphify-Labs/graphify)."
    )


def missing_codex_cli_message() -> str:
    """Actionable error when the Codex binary is not on PATH."""
    return (
        f"error: Codex CLI not found on PATH. {PRODUCT} is a Codex-only variant "
        "and needs the `codex` command.\n"
        "Install OpenAI Codex, then open a new terminal:\n"
        "  https://openai.com/codex/\n"
        f"Then run `{CLI} doctor` to re-check."
    )


def bad_codex_config_message(path: str | None = None) -> str:
    """Actionable error when Codex multi-agent dispatch is unavailable or config is invalid."""
    where = path or "~/.codex/config.toml"
    return (
        f"error: Codex config at {where} is missing or does not enable multi-agent. "
        f"{PRODUCT} parallel extraction needs `multi_agent = true` under `[features]`.\n"
        f"Create or edit {where}:\n"
        "  [features]\n"
        "  multi_agent = true\n"
        "Restart Codex, then retry. A code-only corpus can continue without subagents (AST only)."
    )


def failed_graph_build_message(path: str | None = None, reason: str | None = None) -> str:
    """Actionable error when extract/build produced no usable graph."""
    where = f" at {path}" if path else ""
    why = f" {reason}" if reason else ""
    return (
        f"error: {PRODUCT} graph build failed{where}.{why} "
        "Check the path, ignore rules (`.gitignore` / `.graphifyignore`), and that "
        f"the folder has supported files. Then retry `{TRIGGER} .` or `{CLI} extract . --force`."
    )
