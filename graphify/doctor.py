"""Clean-machine Codex checks and actionable Dreamliner graph errors.

Kept separate from ``validate.py`` so schema checks stay a pure function while
user-facing install/query failures become branded, traceback-free messages.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from graphify.brand import CLI, INVOKE, OUT_DIR, PRODUCT


class DreamlinerError(SystemExit):
    """Exit with a clear stderr message instead of a traceback."""

    def __init__(self, message: str, code: int = 1) -> None:
        print(message, file=sys.stderr)
        super().__init__(code)


def _codex_config_path(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".codex" / "config.toml"


def find_codex_cli() -> str | None:
    """Return the Codex CLI path if it is on PATH."""
    return shutil.which("codex")


def _toml_has_multi_agent(text: str) -> bool:
    """Best-effort parse: ``multi_agent = true`` under ``[features]``.

    Avoids adding a TOML dependency. Codex's documented config is a single
    ``[features]`` table with ``multi_agent = true``. Comments and extra
    whitespace are tolerated; dotted ``[features.something]`` is not the
    required table.
    """
    in_features = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            in_features = line[1:-1].strip() == "features"
            continue
        if not in_features:
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == "multi_agent" and value.strip().lower() in {"true", "1"}:
            return True
    return False


def check_codex_config(home: Path | None = None) -> list[str]:
    """Return actionable problems with ``~/.codex/config.toml``."""
    path = _codex_config_path(home)
    problems: list[str] = []
    if not path.exists():
        problems.append(
            f"{PRODUCT}: missing {path}. Codex parallel extraction needs:\n"
            f"\n"
            f"    [features]\n"
            f"    multi_agent = true\n"
            f"\n"
            f"Create that file, then restart Codex."
        )
        return problems
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        problems.append(
            f"{PRODUCT}: could not read {path}: {exc}.\n"
            f"Fix the file permissions or recreate it with:\n"
            f"\n"
            f"    [features]\n"
            f"    multi_agent = true\n"
        )
        return problems
    if not _toml_has_multi_agent(text):
        problems.append(
            f"{PRODUCT}: {path} is missing `multi_agent = true` under [features].\n"
            f"Add this and restart Codex:\n"
            f"\n"
            f"    [features]\n"
            f"    multi_agent = true\n"
            f"\n"
            f"Without it, `$dreamliner` semantic subagents cannot use spawn_agent."
        )
    return problems


def check_codex_ready(*, home: Path | None = None, require_cli: bool = True) -> list[str]:
    """Return every Codex clean-machine problem (empty list = ready)."""
    problems: list[str] = []
    if require_cli and not find_codex_cli():
        problems.append(
            f"{PRODUCT}: Codex CLI not found on PATH.\n"
            f"Install Codex (https://github.com/openai/codex), confirm `codex`\n"
            f"works in a new shell, then re-run `{CLI} install`."
        )
    problems.extend(check_codex_config(home))
    return problems


def format_problems(problems: list[str]) -> str:
    return "\n\n".join(problems)


def die_if_codex_unready(*, home: Path | None = None, require_cli: bool = True) -> None:
    problems = check_codex_ready(home=home, require_cli=require_cli)
    if problems:
        raise DreamlinerError(format_problems(problems))


def warn_codex_unready(*, home: Path | None = None, require_cli: bool = True) -> None:
    """Print Codex problems without aborting (skill files can still be written)."""
    problems = check_codex_ready(home=home, require_cli=require_cli)
    if not problems:
        return
    print(format_problems(problems), file=sys.stderr)
    print(
        f"\n{PRODUCT} skill files were still written. Fix the items above, "
        f"then open Codex and type `{INVOKE} .`.",
        file=sys.stderr,
    )


def _empty_graph_help(path: Path) -> str:
    return (
        f"{PRODUCT}: graph at {path} is empty or has no nodes "
        f"(extraction produced nothing usable).\n"
        f"Possible causes: no supported files, binary-only corpus, or a failed build.\n"
        f"Rebuild from the project root:\n"
        f"    {INVOKE} .\n"
        f"or: {CLI} extract .\n"
        f"Then re-run query / path / explain. Schema checks still run via "
        f"`{CLI} validate` (``validate_extraction`` / ``assert_valid``)."
    )


def _missing_graph_help(path: Path) -> str:
    return (
        f"{PRODUCT}: graph file not found: {path}.\n"
        f"Build it first from the project root in Codex:\n"
        f"    {INVOKE} .\n"
        f"or: {CLI} extract .\n"
        f"Then query / path / explain against {OUT_DIR}/graph.json."
    )


def require_usable_graph(path: str | Path, *, check_nodes: bool = True) -> dict:
    """Load graph.json or raise DreamlinerError with an actionable message.

    Used by query / path / explain so a clean machine never sees a traceback
    for a missing, unreadable, or empty graph.
    """
    gp = Path(path)
    if not gp.exists():
        raise DreamlinerError(_missing_graph_help(gp))
    try:
        raw = json.loads(gp.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DreamlinerError(
            f"{PRODUCT}: could not parse {gp} ({exc}).\n"
            f"The file is not valid JSON. Rebuild with `{INVOKE} .` or "
            f"`{CLI} extract .`."
        ) from None
    except OSError as exc:
        raise DreamlinerError(
            f"{PRODUCT}: could not read {gp}: {exc}.\n"
            f"Fix permissions or rebuild with `{INVOKE} .`."
        ) from None
    if not isinstance(raw, dict):
        raise DreamlinerError(
            f"{PRODUCT}: {gp} is not a JSON object. Rebuild with `{INVOKE} .`."
        )
    if check_nodes:
        nodes = raw.get("nodes")
        if not isinstance(nodes, list) or len(nodes) == 0:
            raise DreamlinerError(_empty_graph_help(gp))
    return raw


def run_doctor(*, home: Path | None = None, graph: Path | None = None) -> int:
    """Print a clean-machine Codex + graph report. Return process exit code."""
    problems = check_codex_ready(home=home, require_cli=True)
    graph_path = graph or Path(OUT_DIR) / "graph.json"
    if graph_path.exists():
        try:
            require_usable_graph(graph_path)
        except DreamlinerError:
            problems.append(
                f"{PRODUCT}: graph at {graph_path} exists but is empty or unreadable.\n"
                f"Rebuild with `{INVOKE} .` then `{CLI} validate {graph_path}`."
            )
    else:
        print(
            f"{PRODUCT}: no graph at {graph_path} yet — that is OK on a fresh "
            f"machine. After `{CLI} install`, open Codex and run `{INVOKE} .`."
        )
    if problems:
        print(format_problems(problems), file=sys.stderr)
        return 1
    print(f"{PRODUCT}: Codex CLI and ~/.codex/config.toml look ready.")
    if graph_path.exists():
        print(f"{PRODUCT}: graph at {graph_path} has nodes and is readable.")
    return 0
