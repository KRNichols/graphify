"""Machine-ready checks for a Codex-only Dreamliner install."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from graphify.brand import (
    CLI,
    PRODUCT,
    TRIGGER,
    bad_codex_config_message,
    empty_graph_message,
    failed_graph_build_message,
    missing_binary_message,
    missing_codex_cli_message,
    missing_graph_message,
    package_version,
)

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


def _home() -> Path:
    return Path.home()


def _codex_home(home: Path | None = None) -> Path:
    env = os.environ.get("CODEX_HOME")
    if env:
        return Path(env).expanduser()
    return (home or _home()) / ".codex"


def _codex_config_path(home: Path | None = None) -> Path:
    return _codex_home(home) / "config.toml"


def _skill_paths(home: Path | None = None, cwd: Path | None = None) -> list[Path]:
    home = home or _home()
    cwd = cwd or Path(".")
    return [
        cwd / ".codex" / "skills" / "dreamliner" / "SKILL.md",
        home / ".codex" / "skills" / "dreamliner" / "SKILL.md",
        _codex_home(home) / "skills" / "dreamliner" / "SKILL.md",
    ]


def _read_toml(path: Path) -> tuple[dict | None, str | None]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8")), None
    except OSError as exc:
        return None, f"could not read {path}: {exc}"
    except Exception as exc:
        return None, f"invalid TOML in {path}: {exc}"


def _multi_agent_enabled(data: dict) -> bool:
    features = data.get("features")
    if isinstance(features, dict) and features.get("multi_agent") is True:
        return True
    return data.get("multi_agent") is True


def _graph_check(cwd: Path) -> Check:
    from graphify.paths import GRAPHIFY_OUT

    gp = cwd / GRAPHIFY_OUT / "graph.json"
    if not gp.exists():
        return Check(
            "graph",
            False,
            missing_graph_message(str(gp)),
            required=False,
        )
    try:
        text = gp.read_text(encoding="utf-8")
        import json

        payload = json.loads(text)
    except Exception as exc:
        return Check("graph", False, f"error: {PRODUCT} could not load graph {gp}: {exc}.", True)
    nodes = payload.get("nodes") or []
    if not nodes:
        return Check("graph", False, empty_graph_message(str(gp)), True)
    return Check("graph", True, f"{gp} ({len(nodes)} nodes)", False)


def collect_checks(
    *,
    home: Path | None = None,
    cwd: Path | None = None,
    require_graph: bool = False,
) -> list[Check]:
    home = home or _home()
    cwd = (cwd or Path(".")).resolve()
    checks: list[Check] = []

    try:
        import graphify  # noqa: F401

        checks.append(Check("package", True, f"import graphify ({package_version()})"))
    except Exception as exc:
        checks.append(Check("package", False, f"{missing_binary_message()} ({exc})"))

    cli = shutil.which(CLI) or shutil.which("graphify")
    if cli:
        checks.append(Check("cli", True, cli))
    else:
        checks.append(Check("cli", False, missing_binary_message()))

    codex = shutil.which("codex")
    if codex:
        checks.append(Check("codex-cli", True, codex))
    else:
        checks.append(Check("codex-cli", False, missing_codex_cli_message()))

    cfg = _codex_config_path(home)
    if not cfg.exists():
        checks.append(Check("codex-config", False, bad_codex_config_message(str(cfg))))
    else:
        data, err = _read_toml(cfg)
        if err or data is None:
            checks.append(
                Check(
                    "codex-config",
                    False,
                    f"error: Codex config at {cfg} is invalid. {err} "
                    "Fix the TOML, set `[features] multi_agent = true`, restart Codex.",
                )
            )
        elif not _multi_agent_enabled(data):
            checks.append(Check("codex-config", False, bad_codex_config_message(str(cfg))))
        else:
            checks.append(Check("codex-config", True, f"{cfg} (multi_agent = true)"))

    skill = next((p for p in _skill_paths(home, cwd) if p.is_file()), None)
    if skill:
        checks.append(Check("skill", True, str(skill)))
    else:
        checks.append(
            Check(
                "skill",
                False,
                f"error: {PRODUCT} skill not installed. Run `{CLI} install` "
                f"(or `{CLI} install --project`) and restart Codex. "
                f"Expected `{TRIGGER}` at ~/.codex/skills/dreamliner/SKILL.md.",
            )
        )

    graph = _graph_check(cwd)
    if require_graph:
        graph = Check(graph.name, graph.ok, graph.detail, True)
    checks.append(graph)
    return checks


def print_report(checks: list[Check], *, stream=None) -> int:
    stream = stream or sys.stderr
    print(f"{PRODUCT} doctor", file=stream)
    failed = 0
    for check in checks:
        mark = "ok" if check.ok else ("FAIL" if check.required else "warn")
        print(f"  [{mark:<4}] {check.name}: {check.detail}", file=stream)
        if not check.ok and check.required:
            failed += 1
    if failed:
        print(
            f"error: {PRODUCT} is not ready ({failed} required check(s) failed). "
            f"Fix the FAIL items, then retry `{CLI} doctor`.",
            file=stream,
        )
        return 1
    print(f"{PRODUCT} is ready. In Codex type `{TRIGGER} .`", file=stream)
    return 0


def doctor(
    *,
    home: Path | None = None,
    cwd: Path | None = None,
    require_graph: bool = False,
    stream=None,
) -> int:
    return print_report(
        collect_checks(home=home, cwd=cwd, require_graph=require_graph),
        stream=stream,
    )


# Used by extract when a build yields no nodes.
failed_build = failed_graph_build_message
