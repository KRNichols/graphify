"""Actionable Codex/install error helpers — clean-machine failure modes."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from graphify.errors import (
    Issue,
    check_codex_config,
    check_graph_outputs,
    check_sidecar,
    check_skill_host_path,
    check_toolchain,
    collect_codex_issues,
    diagnose_import_error,
    empty_graph_issue,
    expected_codex_skill_path,
    format_issue,
    format_issues,
    missing_graph_issue,
    run_check,
)


def test_format_issue_is_error_plus_next_step():
    text = format_issue(Issue("x", "something broke", "do this next"))
    assert text.startswith("error: something broke")
    assert "  next: do this next" in text
    assert "hookSpecificOutput" not in text
    assert "additionalContext" not in text


# --- 1. Missing Python / uv / pipx / CLI not on PATH ----------------------


def test_toolchain_missing_python_uv_pipx_and_cli():
    issues = check_toolchain(which=lambda _name: None)
    codes = {i.code for i in issues}
    assert "toolchain.python" in codes
    assert "toolchain.cli" in codes
    assert "toolchain.installer" in codes
    blob = format_issues(issues)
    assert "Python is not on PATH" in blob
    assert "uv tool install graphifyy" in blob
    assert "pipx" in blob


def test_toolchain_graphify_on_path_is_ok_even_without_uv():
    def which(name: str) -> str | None:
        if name in {"python3", "graphify"}:
            return f"/usr/bin/{name}"
        return None

    assert check_toolchain(which=which) == []


def test_toolchain_uv_present_but_cli_missing_points_at_uv_tool():
    def which(name: str) -> str | None:
        if name == "python3":
            return "/usr/bin/python3"
        if name == "uv":
            return "/usr/bin/uv"
        return None

    issues = check_toolchain(which=which)
    assert [i.code for i in issues] == ["toolchain.cli"]
    assert "uv tool install graphifyy" in issues[0].next_step


# --- 2. Missing or broken Codex config ------------------------------------


def test_codex_config_missing_includes_multi_agent_template(tmp_path):
    issues = check_codex_config(tmp_path / "config.toml")
    assert issues[0].code == "codex.config.missing"
    assert "multi_agent = true" in issues[0].next_step
    assert "[features]" in issues[0].next_step


def test_codex_config_broken_toml(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("features = [\n", encoding="utf-8")
    issues = check_codex_config(path)
    assert issues[0].code == "codex.config.broken"
    assert "not valid TOML" in issues[0].title


def test_codex_config_missing_multi_agent_note(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[features]\nfoo = true\n", encoding="utf-8")
    issues = check_codex_config(path)
    assert issues[0].code == "codex.config.multi_agent"
    assert "spawn_agent" in issues[0].next_step


def test_codex_config_ok_with_multi_agent(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[features]\nmulti_agent = true\n", encoding="utf-8")
    assert check_codex_config(path) == []


def test_codex_home_env_override(tmp_path):
    profile = tmp_path / "profile"
    issues = check_codex_config(home=tmp_path, env={"CODEX_HOME": str(profile)})
    assert str(profile / "config.toml") in issues[0].title


# --- 3. Skill install wrote to the wrong host path ------------------------


def test_skill_wrong_host_claude_path(tmp_path):
    wrong = tmp_path / ".claude" / "skills" / "graphify" / "SKILL.md"
    issues = check_skill_host_path(wrong, home=tmp_path)
    assert issues[0].code == "skill.wrong_host"
    assert "Codex will not load this" in issues[0].title
    assert "install --platform codex" in issues[0].next_step


def test_skill_missing_points_at_misplaced_claude_copy(tmp_path):
    claude = tmp_path / ".claude" / "skills" / "graphify" / "SKILL.md"
    claude.parent.mkdir(parents=True)
    claude.write_text("# graphify\n", encoding="utf-8")
    issues = check_skill_host_path(home=tmp_path, project_dir=tmp_path)
    codes = {i.code for i in issues}
    assert "skill.missing" in codes
    blob = format_issues(issues)
    assert str(claude) in blob


def test_skill_expected_project_path(tmp_path):
    dst = expected_codex_skill_path(project=True, project_dir=tmp_path)
    dst.parent.mkdir(parents=True)
    dst.write_text("# graphify\n", encoding="utf-8")
    assert check_skill_host_path(dst, project=True, project_dir=tmp_path) == []


# --- 4. Import / sidecar contract -----------------------------------------


def test_sidecar_missing_is_loud():
    issues = check_sidecar(Path("/no/such/.graphify_python"))
    assert issues[0].code == "sidecar.missing"
    assert "sidecar" in issues[0].title
    assert "import graphify" in issues[0].next_step


def test_sidecar_stale_interpreter(tmp_path):
    side = tmp_path / ".graphify_python"
    side.write_text(str(tmp_path / "gone-python"), encoding="utf-8")
    issues = check_sidecar(side)
    assert issues[0].code == "sidecar.stale"
    assert "missing interpreter" in issues[0].title


def test_sidecar_wrong_interpreter_cannot_import(tmp_path):
    """A sidecar pointing at a python without graphify must not stay silent."""
    fake = tmp_path / "no-graphify-python"
    fake.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    fake.chmod(0o755)
    side = tmp_path / ".graphify_python"
    side.write_text(str(fake), encoding="utf-8")
    issues = check_sidecar(side)
    assert issues[0].code == "sidecar.no_graphify"
    assert "cannot import graphify" in issues[0].title
    assert "sidecar contract" in issues[0].next_step


def test_diagnose_import_error_mentions_sidecar_not_raw_module():
    issues = diagnose_import_error(
        ModuleNotFoundError("No module named 'graphify'"),
        sidecar=Path("/tmp/.graphify_python"),
    )
    blob = format_issues(issues)
    assert "cannot import graphify" in blob
    assert "sidecar" in blob
    # The helper is the diagnosis — callers should print this, not the traceback.
    assert "ModuleNotFoundError" in blob or "graphify-out/.graphify_python" in blob


# --- 5. Failed / empty graph outputs --------------------------------------


def test_empty_graph_has_clear_next_step():
    issue = empty_graph_issue()
    assert issue.code == "graph.empty"
    assert "no nodes" in issue.title
    assert "graphify extract ." in issue.next_step
    assert "do not label" in issue.next_step.lower() or "stop" in issue.next_step


def test_missing_graph_keeps_legacy_phrase_and_adds_next():
    issue = missing_graph_issue(Path("/tmp/graphify-out/graph.json"))
    assert "graph file not found" in issue.title
    assert "graphify extract ." in issue.next_step


def test_graph_artifacts_without_json(tmp_path):
    (tmp_path / ".graphify_extract.json").write_text("{}", encoding="utf-8")
    issues = check_graph_outputs(tmp_path)
    assert issues[0].code == "graph.missing_after_build"
    assert "was not written" in issues[0].title


def test_empty_graph_json_file(tmp_path):
    (tmp_path / "graph.json").write_text(
        json.dumps({"nodes": [], "links": []}), encoding="utf-8"
    )
    issues = check_graph_outputs(tmp_path)
    assert issues[0].code == "graph.empty"


def test_fresh_machine_without_build_is_not_empty_graph_error(tmp_path):
    assert check_graph_outputs(tmp_path) == []


# --- 6. hook-check stays a silent no-op (see also test_hooks.py) -----------


def test_hook_check_never_emits_claude_hook_payload(tmp_path):
    """Codex PreToolUse must not receive hookSpecificOutput / additionalContext."""
    out = tmp_path / "graphify-out"
    out.mkdir()
    (out / "graph.json").write_text("{}", encoding="utf-8")
    stdin = json.dumps({
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
    })
    result = subprocess.run(
        [sys.executable, "-m", "graphify", "hook-check"],
        cwd=tmp_path,
        input=stdin,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    assert "hookSpecificOutput" not in result.stdout
    assert "additionalContext" not in result.stdout


def test_errors_module_doc_forbids_hook_check_use():
    from graphify import errors as err_mod

    assert "hook-check" in err_mod.__doc__
    assert "silent" in err_mod.__doc__


# --- graphify check CLI ---------------------------------------------------


def test_run_check_exit_codes(tmp_path, monkeypatch):
    monkeypatch.setattr("graphify.errors.codex_home", lambda home=None, env=None: tmp_path / ".codex")
    # Empty PATH-like which() forces toolchain issues → nonzero.
    issues = collect_codex_issues(
        home=tmp_path,
        project_dir=tmp_path,
        env={},
        which=lambda _n: None,
        out_dir=tmp_path / "graphify-out",
    )
    assert any(i.code.startswith("toolchain") for i in issues)
    assert run_check(project=True, project_dir=tmp_path) in (0, 1)


def test_codex_skill_documents_check_and_hook_noop():
    import graphify

    skill = (Path(graphify.__file__).parent / "skill-codex.md").read_text(encoding="utf-8")
    assert "## Codex clean-machine failures" in skill
    assert "graphify check" in skill
    assert "hook-check" in skill
    assert "multi_agent" in skill
    assert "hookSpecificOutput" in skill


def test_codex_platform_install_warns_on_missing_config(tmp_path, capsys, monkeypatch):
    from graphify.install import install

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    old = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        install(platform="codex")
    finally:
        os.chdir(old)
    err = capsys.readouterr().err
    assert (tmp_path / ".codex" / "skills" / "graphify" / "SKILL.md").exists()
    assert "Codex config missing" in err
    assert "  next:" in err
    assert "multi_agent = true" in err
    assert "hookSpecificOutput" not in err


def test_claude_install_does_not_emit_codex_preflight(tmp_path, capsys, monkeypatch):
    from graphify.install import install

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    old = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        install(platform="claude")
    finally:
        os.chdir(old)
    assert "Codex config missing" not in capsys.readouterr().err


def test_graphify_check_cli_lists_issues(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "graphify", "check"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={**dict(**{k: v for k, v in __import__("os").environ.items()}),
             "CODEX_HOME": str(tmp_path / "no-such-codex")},
    )
    # Either ok (this machine has graphify on PATH + config) or issues.
    assert result.returncode in (0, 1)
    blob = result.stdout + result.stderr
    assert "graphify check:" in blob
    assert "hookSpecificOutput" not in blob
