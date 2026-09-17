"""Actionable error helpers for clean-machine Codex/install failures.

Reused by ``graphify install --platform codex``, ``graphify codex install``,
and ``graphify check``. These helpers print human text only.

Do not call this module from ``hook-check``. That path must stay a silent
no-op: Codex Desktop rejects Claude-style ``hookSpecificOutput`` /
``additionalContext`` on PreToolUse, and a nonzero exit would break every
Bash tool call.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence
import os
import shutil
import sys

Which = Callable[[str], str | None]


@dataclass(frozen=True)
class Issue:
    """One clean-machine failure with a next step."""

    code: str
    title: str
    next_step: str

    def format(self) -> str:
        return format_issue(self)


def format_issue(issue: Issue) -> str:
    """Render one issue as ``error:`` + ``next:`` lines."""
    nxt = issue.next_step.strip()
    first, *rest = nxt.splitlines() or [""]
    lines = [f"error: {issue.title}", f"  next: {first}"]
    lines.extend(f"        {line}" for line in rest)
    return "\n".join(lines)


def format_issues(issues: Sequence[Issue]) -> str:
    return "\n\n".join(format_issue(issue) for issue in issues)


def emit_issues(issues: Sequence[Issue], *, file=None) -> None:
    if not issues:
        return
    print(format_issues(issues), file=file or sys.stderr)


def die(issues: Sequence[Issue], code: int = 1) -> None:
    emit_issues(issues)
    raise SystemExit(code)


def codex_home(home: Path | None = None, env: dict[str, str] | None = None) -> Path:
    """Codex config root: ``$CODEX_HOME`` or ``~/.codex``."""
    environ = env if env is not None else os.environ
    override = environ.get("CODEX_HOME")
    if override:
        return Path(override).expanduser()
    return (home or Path.home()) / ".codex"


def expected_codex_skill_path(
    *,
    project: bool = False,
    project_dir: Path | None = None,
    home: Path | None = None,
    env: dict[str, str] | None = None,
) -> Path:
    if project:
        return (project_dir or Path(".")) / ".codex" / "skills" / "graphify" / "SKILL.md"
    return codex_home(home, env) / "skills" / "graphify" / "SKILL.md"


def sidecar_path(out_dir: Path | None = None) -> Path:
    from graphify.paths import GRAPHIFY_OUT

    return (out_dir or Path(GRAPHIFY_OUT)) / ".graphify_python"


# ---------------------------------------------------------------------------
# 1. Missing Python / uv / pipx / CLI not on PATH
# ---------------------------------------------------------------------------


def check_toolchain(*, which: Which | None = None) -> list[Issue]:
    """Detect a clean machine that cannot run graphify or install it."""
    lookup = which or shutil.which
    python = lookup("python3") or lookup("python")
    uv = lookup("uv")
    pipx = lookup("pipx")
    cli = lookup("graphify")
    issues: list[Issue] = []

    if not python:
        issues.append(
            Issue(
                code="toolchain.python",
                title="Python is not on PATH (python3 / python)",
                next_step=(
                    "install Python 3.10+ from https://www.python.org/downloads/ "
                    "and reopen the terminal so `python3 --version` works. "
                    "On macOS, `xcode-select --install` also provides python3."
                ),
            )
        )

    if not cli:
        installer = (
            "`uv tool install graphifyy` then `uv tool update-shell` "
            "(adds ~/.local/bin to PATH)"
            if uv
            else (
                "`pipx install graphifyy` then `pipx ensurepath`"
                if pipx
                else (
                    "install uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`) "
                    "and run `uv tool install graphifyy`, or `pipx install graphifyy`"
                )
            )
        )
        issues.append(
            Issue(
                code="toolchain.cli",
                title="graphify CLI is not on PATH",
                next_step=(
                    f"{installer}. Codex hooks call `graphify hook-check`; "
                    "without PATH, project-scoped hooks cannot start."
                ),
            )
        )

    if not cli and not uv and not pipx:
        issues.append(
            Issue(
                code="toolchain.installer",
                title="neither uv nor pipx is on PATH (cannot install graphifyy)",
                next_step=(
                    "install uv from https://docs.astral.sh/uv/getting-started/installation/ "
                    "(recommended), or pipx (`python3 -m pip install --user pipx && pipx ensurepath`). "
                    "Then `uv tool install graphifyy` or `pipx install graphifyy`."
                ),
            )
        )
    return issues


# ---------------------------------------------------------------------------
# 2. Missing or broken Codex config (incl. multi_agent)
# ---------------------------------------------------------------------------


def check_codex_config(
    path: Path | None = None,
    *,
    home: Path | None = None,
    env: dict[str, str] | None = None,
    need_multi_agent: bool = True,
) -> list[Issue]:
    """Detect a missing/broken ~/.codex/config.toml.

    ``need_multi_agent`` adds a note when ``[features].multi_agent`` is not
    true — required for Codex ``spawn_agent`` parallel extraction.
    """
    config = path or (codex_home(home, env) / "config.toml")
    issues: list[Issue] = []
    if not config.exists():
        extra = (
            "\n\n[features]\nmulti_agent = true\n"
            if need_multi_agent
            else ""
        )
        issues.append(
            Issue(
                code="codex.config.missing",
                title=f"Codex config missing ({config})",
                next_step=(
                    f"create {config} (Codex writes one on first launch). "
                    "For parallel $graphify extraction via spawn_agent, add:"
                    f"{extra}\nthen restart Codex."
                ),
            )
        )
        return issues

    data, parse_err = _read_toml(config)
    if data is None:
        issues.append(
            Issue(
                code="codex.config.broken",
                title=f"Codex config is not valid TOML ({config})",
                next_step=(
                    f"fix the TOML syntax ({parse_err}) or move the file aside "
                    f"and let Codex recreate it. Keep "
                    f"`[features] multi_agent = true` if you use spawn_agent."
                ),
            )
        )
        return issues

    if need_multi_agent and not _toml_multi_agent_enabled(data):
        issues.append(
            Issue(
                code="codex.config.multi_agent",
                title=f"Codex config has no [features] multi_agent = true ({config})",
                next_step=(
                    "add the following and restart Codex; without it spawn_agent "
                    "is unavailable and $graphify falls back to sequential extraction:\n"
                    "\n[features]\nmulti_agent = true"
                ),
            )
        )
    return issues


def _read_toml(path: Path) -> tuple[dict | None, str]:
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10
        import tomli as tomllib  # type: ignore[no-redef]
    try:
        return tomllib.loads(path.read_text(encoding="utf-8")), ""
    except Exception as exc:
        return None, f"{exc.__class__.__name__}: {exc}"


def _toml_multi_agent_enabled(data: dict) -> bool:
    features = data.get("features")
    if not isinstance(features, dict):
        return False
    return features.get("multi_agent") is True


# ---------------------------------------------------------------------------
# 3. Skill install wrote to the wrong host path
# ---------------------------------------------------------------------------


def check_skill_host_path(
    skill_dst: Path | None = None,
    *,
    project: bool = False,
    project_dir: Path | None = None,
    home: Path | None = None,
    env: dict[str, str] | None = None,
) -> list[Issue]:
    """Detect a skill that landed where Codex will not load it."""
    expected = expected_codex_skill_path(
        project=project, project_dir=project_dir, home=home, env=env
    )
    issues: list[Issue] = []
    dst = skill_dst or expected

    if ".codex" not in dst.parts:
        issues.append(
            Issue(
                code="skill.wrong_host",
                title=f"skill installed at {dst} — Codex will not load this",
                next_step=(
                    f"Codex reads {expected}. Re-run "
                    f"`graphify install --platform codex` (user) or "
                    f"`graphify install --project --platform codex` (this repo). "
                    "Do not use --platform claude on a Codex machine."
                ),
            )
        )
        return issues

    try:
        dst_resolved = dst.expanduser().resolve()
        expected_resolved = expected.expanduser().resolve()
    except OSError:
        dst_resolved = dst
        expected_resolved = expected
    if dst_resolved != expected_resolved:
        issues.append(
            Issue(
                code="skill.wrong_host",
                title=f"skill installed at {dst} but Codex expects {expected}",
                next_step=(
                    "CODEX_HOME or --project scope does not match the path that "
                    "was written. Re-run the Codex installer from the repo you "
                    "want Codex to see, or set CODEX_HOME to the profile Codex uses."
                ),
            )
        )

    if not dst.exists() and not expected.exists():
        misplaced = _find_misplaced_skill(home or Path.home(), project_dir or Path("."))
        hint = (
            f" Found a graphify skill at {misplaced} instead — that host is not Codex."
            if misplaced
            else ""
        )
        issues.append(
            Issue(
                code="skill.missing",
                title=f"Codex skill not found at {expected}.{hint}",
                next_step=(
                    "run `graphify install --platform codex` to write "
                    "~/.codex/skills/graphify/SKILL.md, or "
                    "`graphify install --project --platform codex` for "
                    "./.codex/skills/graphify/SKILL.md. Then `$graphify` in Codex."
                ),
            )
        )
    return issues


def _find_misplaced_skill(home: Path, project_dir: Path) -> Path | None:
    candidates = [
        home / ".claude" / "skills" / "graphify" / "SKILL.md",
        home / ".codebuddy" / "skills" / "graphify" / "SKILL.md",
        home / ".gemini" / "skills" / "graphify" / "SKILL.md",
        project_dir / ".claude" / "skills" / "graphify" / "SKILL.md",
        project_dir / ".cursor" / "rules" / "graphify.mdc",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


# ---------------------------------------------------------------------------
# 4. Import / .graphify_python sidecar contract
# ---------------------------------------------------------------------------


def check_sidecar(path: Path | None = None) -> list[Issue]:
    """Loud diagnosis for a missing, stale, or wrong-interpreter sidecar."""
    side = path or sidecar_path()
    if not side.exists():
        return [
            Issue(
                code="sidecar.missing",
                title=f"sidecar {side} is missing",
                next_step=(
                    "this file records the Python that can `import graphify`. "
                    "Re-run `$graphify` (skill Step 1) or: "
                    "mkdir -p graphify-out && python3 -c \"import sys; "
                    "open('graphify-out/.graphify_python','w').write(sys.executable)\" "
                    "using the same interpreter that has graphifyy installed."
                ),
            )
        ]

    raw = side.read_text(encoding="utf-8").strip()
    if not raw:
        return [
            Issue(
                code="sidecar.empty",
                title=f"sidecar {side} is empty",
                next_step=(
                    f"delete {side} and re-run `$graphify` so Step 1 rewrites it "
                    "from the interpreter that can `import graphify`."
                ),
            )
        ]

    interp = Path(raw)
    if not interp.exists():
        return [
            Issue(
                code="sidecar.stale",
                title=f"sidecar {side} points at missing interpreter {raw}",
                next_step=(
                    f"delete {side} (uv/pipx reinstalls move the venv) and re-run "
                    "`$graphify`, or `uv tool install --reinstall graphifyy`."
                ),
            )
        ]

    if not _interpreter_has_graphify(interp):
        return [
            Issue(
                code="sidecar.no_graphify",
                title=f"{raw} (from {side}) cannot import graphify",
                next_step=(
                    f"this is the sidecar contract: every skill bash block runs "
                    f"`$(cat {side})`, so a system python3 without graphifyy "
                    f"yields ModuleNotFoundError. Delete {side} and re-run "
                    f"`$graphify`, or install with `uv tool install graphifyy` "
                    f"and write that tool's `python` path into {side}."
                ),
            )
        ]
    return []


def diagnose_import_error(
    exc: BaseException | None = None,
    *,
    sidecar: Path | None = None,
) -> list[Issue]:
    """Replace a raw ModuleNotFoundError with a sidecar-aware diagnosis."""
    name = getattr(exc, "name", None) if exc is not None else None
    detail = f" ({exc})" if exc is not None else ""
    issues = [
        Issue(
            code="import.graphify",
            title=f"cannot import graphify{detail}",
            next_step=(
                "this is almost never a missing pip extra — it means the "
                "interpreter running this command is not the one graphifyy "
                "was installed into. Check graphify-out/.graphify_python "
                "(the sidecar written by $graphify Step 1). If it is missing, "
                "stale, or points at system python3, delete it and re-run "
                "`$graphify` or `uv tool install graphifyy`."
                + (f" Missing module name: {name}." if name else "")
            ),
        )
    ]
    issues.extend(check_sidecar(sidecar or sidecar_path()))
    return issues


def _interpreter_has_graphify(interp: Path) -> bool:
    import subprocess

    try:
        result = subprocess.run(
            [str(interp), "-c", "import importlib.util, sys; "
             "sys.exit(0 if importlib.util.find_spec('graphify') else 1)"],
            capture_output=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


# ---------------------------------------------------------------------------
# 5. Failed graph build / empty outputs
# ---------------------------------------------------------------------------


def check_graph_outputs(
    out_dir: Path | None = None,
    *,
    nodes: int | None = None,
    require_graph: bool = False,
) -> list[Issue]:
    """Detect a failed or empty graph build and give the next command.

    ``require_graph=False`` (used by ``graphify check``) only fires when a
    build was attempted (extract/detect sidecars present) or ``graph.json``
    exists but is empty. ``require_graph=True`` is for query/path/explain.
    """
    from graphify.paths import GRAPHIFY_OUT

    out = out_dir or Path(GRAPHIFY_OUT)
    graph = out / "graph.json"
    extract = out / ".graphify_extract.json"
    detect = out / ".graphify_detect.json"
    report = out / "GRAPH_REPORT.md"
    attempted = extract.exists() or detect.exists() or graph.exists()

    if nodes == 0 or (graph.exists() and _graph_node_count(graph) == 0):
        return [
            Issue(
                code="graph.empty",
                title="graph build produced no nodes (graphify-out/graph.json empty)",
                next_step=(
                    "stop — do not label or visualize an empty graph. "
                    "Re-run `graphify extract .` from the project root. "
                    "If detect reported 0 files, the path is wrong or "
                    ".gitignore/.graphifyignore excluded everything. "
                    "If extract ran, inspect graphify-out/.graphify_extract.json."
                ),
            )
        ]

    if require_graph and not graph.exists():
        return [missing_graph_issue(graph)]

    if attempted and not graph.exists():
        return [
            Issue(
                code="graph.missing_after_build",
                title=f"extraction artifacts exist but {graph} was not written",
                next_step=(
                    "the last build failed before export. Re-run "
                    "`graphify extract .` and read the error above this line. "
                    f"{'GRAPH_REPORT.md is also missing. ' if not report.exists() else ''}"
                    "Do not treat a leftover .graphify_extract.json as a graph."
                ),
            )
        ]
    return []


def missing_graph_issue(path: Path) -> Issue:
    return Issue(
        code="graph.missing",
        title=f"graph file not found: {path}",
        next_step=(
            "run `graphify extract .` from the project root "
            "(or `$graphify .` in Codex) to create graphify-out/graph.json. "
            "If this is a worktree, set GRAPHIFY_OUT or pass --graph."
        ),
    )


def emit_missing_graph(path: Path, *, file=None) -> None:
    emit_issues([missing_graph_issue(path)], file=file)


def empty_graph_issue() -> Issue:
    return check_graph_outputs(nodes=0)[0]


def _graph_node_count(graph: Path) -> int | None:
    import json

    try:
        data = json.loads(graph.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    nodes = data.get("nodes")
    if isinstance(nodes, list):
        return len(nodes)
    return None


# ---------------------------------------------------------------------------
# Combined preflight / CLI entry
# ---------------------------------------------------------------------------


def collect_codex_issues(
    *,
    project: bool = False,
    project_dir: Path | None = None,
    skill_dst: Path | None = None,
    home: Path | None = None,
    env: dict[str, str] | None = None,
    which: Which | None = None,
    out_dir: Path | None = None,
    need_multi_agent: bool = True,
    require_graph: bool = False,
) -> list[Issue]:
    """All Codex clean-machine checks in one list (order matches the user list)."""
    issues: list[Issue] = []
    issues.extend(check_toolchain(which=which))
    issues.extend(
        check_codex_config(home=home, env=env, need_multi_agent=need_multi_agent)
    )
    issues.extend(
        check_skill_host_path(
            skill_dst,
            project=project,
            project_dir=project_dir,
            home=home,
            env=env,
        )
    )
    side = sidecar_path(out_dir)
    if side.exists() or require_graph:
        issues.extend(check_sidecar(side))
    issues.extend(check_graph_outputs(out_dir, require_graph=require_graph))
    return issues


def report_codex_install(
    *,
    project: bool = False,
    project_dir: Path | None = None,
    skill_dst: Path | None = None,
    home: Path | None = None,
) -> list[Issue]:
    """Post-install warnings. Does not exit — the install itself succeeded."""
    issues = collect_codex_issues(
        project=project,
        project_dir=project_dir,
        skill_dst=skill_dst,
        home=home,
    )
    if issues:
        emit_issues(issues)
        print(
            "  (install itself succeeded; fix the items above so Codex can use graphify)",
            file=sys.stderr,
        )
    return issues


def run_check(
    *,
    project: bool = False,
    project_dir: Path | None = None,
    file=None,
) -> int:
    """CLI body for ``graphify check``. Returns an exit code; does not sys.exit."""
    dest = file or sys.stderr
    issues = collect_codex_issues(project=project, project_dir=project_dir)
    if not issues:
        print("graphify check: ok", file=dest)
        return 0
    emit_issues(issues, file=dest)
    print(f"graphify check: {len(issues)} issue(s)", file=dest)
    return 1
