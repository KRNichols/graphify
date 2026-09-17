"""Tests for the Codex-only install surface."""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


def _install(tmp_path, platform="codex"):
    from graphify.__main__ import install

    old_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        with patch("graphify.__main__.Path.home", return_value=tmp_path):
            install(platform=platform)
    finally:
        os.chdir(old_cwd)


def _agents_install(tmp_path, platform="codex"):
    from graphify.__main__ import _agents_install as _install_fn

    _install_fn(tmp_path, platform)


def _agents_uninstall(tmp_path, platform="codex"):
    from graphify.__main__ import _agents_uninstall as _uninstall_fn

    _uninstall_fn(tmp_path, platform=platform)


def test_install_default_is_codex():
    from graphify.install import _DEFAULT_PLATFORM, install

    assert _DEFAULT_PLATFORM == "codex"
    assert install.__defaults__[0] == "codex"


def test_install_codex(tmp_path):
    _install(tmp_path, "codex")
    assert (tmp_path / ".codex" / "skills" / "graphify" / "SKILL.md").exists()


def test_install_survives_a_winerror_17_replace(tmp_path, monkeypatch):
    """#3508: SKILL.md install must fall back when os.replace raises WinError 17."""
    real_replace = os.replace

    def flaky_replace(src, dst):
        # Progressive Codex installs also replace the references/ directory.
        # This regression is about the SKILL.md file replace only.
        if Path(dst).name != "SKILL.md":
            return real_replace(src, dst)
        exc = OSError("cannot move to a different disk drive")
        exc.winerror = 17
        raise exc

    monkeypatch.setattr(os, "replace", flaky_replace)
    try:
        _install(tmp_path, "codex")
    finally:
        monkeypatch.setattr(os, "replace", real_replace)

    skill = tmp_path / ".codex" / "skills" / "graphify" / "SKILL.md"
    assert skill.exists()
    assert not any(p.name.endswith(".tmp") for p in skill.parent.iterdir())


def test_bare_install_targets_codex(tmp_path, monkeypatch):
    from graphify.__main__ import main

    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "argv", ["graphify", "install"])
    with patch("graphify.__main__.Path.home", return_value=home):
        main()
    assert (home / ".codex" / "skills" / "graphify" / "SKILL.md").exists()
    assert not (home / ".claude" / "skills" / "graphify" / "SKILL.md").exists()
    assert not (home / ".agents" / "skills").exists()


def test_install_other_platform_is_gated(tmp_path):
    with pytest.raises(SystemExit) as exc:
        _install(tmp_path, "claude")
    assert exc.value.code == 1
    assert not (tmp_path / ".claude").exists()


@pytest.mark.parametrize(
    "argv",
    [
        ["graphify", "install", "--platform", "claude"],
        ["graphify", "install", "opencode"],
        ["graphify", "claude", "install"],
        ["graphify", "cursor", "install"],
        ["graphify", "gemini", "install"],
        ["graphify", "copilot", "install"],
    ],
)
def test_cli_other_hosts_are_gated(tmp_path, monkeypatch, argv, capsys):
    from graphify.__main__ import main

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", argv)
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Codex-only" in err
    assert not (tmp_path / ".claude").exists()
    assert not (tmp_path / ".cursor").exists()
    assert not (tmp_path / ".gemini").exists()
    assert not (tmp_path / ".copilot").exists()


def test_install_help_is_codex_only(tmp_path, monkeypatch, capsys):
    from graphify.__main__ import main

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["graphify", "install", "--help"])
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        main()
    out = capsys.readouterr().out
    assert "Usage: graphify install" in out
    assert "codex" in out.lower()
    assert "claude" not in out.lower()
    assert "opencode" not in out.lower()
    assert not (tmp_path / ".codex").exists()


def test_top_level_help_is_codex_only(monkeypatch, capsys):
    from graphify.__main__ import main

    monkeypatch.setattr(sys, "argv", ["graphify", "--help"])
    main()
    out = capsys.readouterr().out
    assert "default platform: codex" in out
    assert "codex install" in out
    assert "claude install" not in out
    assert "cursor install" not in out
    assert "gemini install" not in out


def test_install_project_codex_writes_skill_and_agents(tmp_path, monkeypatch):
    from graphify.__main__ import main

    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setattr(sys, "argv", ["graphify", "install", "--project"])
    with patch("graphify.__main__.Path.home", return_value=home):
        main()
    assert (project / ".codex" / "skills" / "graphify" / "SKILL.md").exists()
    assert (project / "AGENTS.md").exists()
    assert (project / ".codex" / "hooks.json").exists()
    assert not (home / ".codex" / "skills" / "graphify" / "SKILL.md").exists()


def test_codex_subcommand_project_install_and_uninstall_are_project_scoped(tmp_path, monkeypatch):
    from graphify.__main__ import main

    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()
    user_skill = home / ".codex" / "skills" / "graphify" / "SKILL.md"
    user_skill.parent.mkdir(parents=True)
    user_skill.write_text("user skill")
    monkeypatch.chdir(project)
    with patch("graphify.__main__.Path.home", return_value=home):
        monkeypatch.setattr(sys, "argv", ["graphify", "codex", "install", "--project"])
        main()
        assert (project / ".codex" / "skills" / "graphify" / "SKILL.md").exists()
        assert (project / "AGENTS.md").exists()
        assert (project / ".codex" / "hooks.json").exists()
        assert user_skill.exists()

        monkeypatch.setattr(sys, "argv", ["graphify", "codex", "uninstall", "--project"])
        main()

    assert user_skill.exists()
    assert not (project / ".codex" / "skills" / "graphify" / "SKILL.md").exists()
    assert not (project / "AGENTS.md").exists()
    hooks_path = project / ".codex" / "hooks.json"
    assert hooks_path.exists()
    assert "graphify" not in hooks_path.read_text()


def test_codex_skill_contains_spawn_agent():
    import graphify

    skill = (Path(graphify.__file__).parent / "skill-codex.md").read_text()
    assert "spawn_agent" in skill


def test_codex_skill_uses_graphify_with_existing_graph():
    import graphify

    skill = (Path(graphify.__file__).parent / "skill-codex.md").read_text()
    assert "Fast path — existing graph" in skill
    assert "skip Steps 1–5 entirely and jump straight to `## For /graphify query`" in skill
    assert "graphify query" in skill
    assert "graphify explain" in skill
    assert "graphify path" in skill


def test_codex_skill_hooks_point_at_agents_md():
    import graphify

    skill = (Path(graphify.__file__).parent / "skill-codex.md").read_text()
    assert "AGENTS.md" in skill
    assert "native CLAUDE.md integration" not in skill
    hooks = (
        Path(graphify.__file__).parent / "skills" / "codex" / "references" / "hooks.md"
    ).read_text()
    assert "AGENTS.md" in hooks
    assert "graphify claude install" not in hooks


def test_only_codex_skill_body_ships_in_package():
    import graphify

    pkg = Path(graphify.__file__).parent
    assert (pkg / "skill-codex.md").exists()
    leftover = sorted(
        p.name for p in pkg.glob("skill*.md") if p.name != "skill-codex.md"
    )
    assert leftover == []
    assert not (pkg / "command-kilo.md").exists()
    assert [p.name for p in (pkg / "skills").iterdir() if p.is_dir()] == ["codex"]
    assert [p.name for p in (pkg / "always_on").glob("*.md")] == ["agents-md.md"]


def test_codex_install_does_not_write_claude_md(tmp_path):
    _install(tmp_path, "codex")
    assert not (tmp_path / ".claude" / "CLAUDE.md").exists()


def test_codex_agents_install_mentions_dirty_graph_output(tmp_path):
    _agents_install(tmp_path, "codex")
    content = (tmp_path / "AGENTS.md").read_text()
    assert "Dirty graphify-out/ files are expected" in content
    assert "not a reason to skip graphify" in content


def test_codex_agents_install_writes_agents_md(tmp_path):
    _agents_install(tmp_path, "codex")
    agents_md = tmp_path / "AGENTS.md"
    assert agents_md.exists()
    assert "graphify" in agents_md.read_text()
    assert "GRAPH_REPORT.md" in agents_md.read_text()


def test_agents_install_idempotent(tmp_path):
    _agents_install(tmp_path, "codex")
    _agents_install(tmp_path, "codex")
    content = (tmp_path / "AGENTS.md").read_text()
    assert content.count("## graphify") == 1


def test_agents_install_appends_to_existing(tmp_path):
    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text("# Existing rules\n\nDo not break things.\n")
    _agents_install(tmp_path, "codex")
    content = agents_md.read_text()
    assert "Do not break things." in content
    assert "## graphify" in content


def test_agents_uninstall_removes_section(tmp_path):
    _agents_install(tmp_path, "codex")
    _agents_uninstall(tmp_path)
    assert not (tmp_path / "AGENTS.md").exists()


def test_agents_uninstall_preserves_other_content(tmp_path):
    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text("# Existing rules\n\nDo not break things.\n")
    _agents_install(tmp_path, "codex")
    _agents_uninstall(tmp_path)
    assert agents_md.exists()
    content = agents_md.read_text()
    assert "Do not break things." in content
    assert "## graphify" not in content


def test_agents_uninstall_no_op_when_not_installed(tmp_path, capsys):
    _agents_uninstall(tmp_path)
    out = capsys.readouterr().out
    assert "nothing to do" in out


def test_remove_marker_section_matches_exact_heading_only():
    from graphify.install import _remove_marker_section

    m = "## graphify"
    assert _remove_marker_section("# Doc\n\n### graphify\n\nmy notes\n", m) is None
    assert _remove_marker_section("see the ## graphify bullet\n", m) is None

    content = "# Doc\n\n### graphify\n\nmy notes\n\n## graphify\n\ngraphify stuff\n"
    out = _remove_marker_section(content, m)
    assert out is not None
    assert "### graphify" in out and "my notes" in out
    assert not any(line.strip() == "## graphify" for line in out.splitlines())
    assert "graphify stuff" not in out


def test_agents_uninstall_preserves_user_h3_graphify_heading(tmp_path):
    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text(
        "# My rules\n\n"
        "### graphify\n\n"
        "My own notes on how I use graphify. Keep this.\n\n"
        "## Other\n\nUnrelated content.\n"
    )
    _agents_install(tmp_path, "codex")
    _agents_uninstall(tmp_path)
    content = agents_md.read_text()
    assert "### graphify" in content
    assert "My own notes on how I use graphify. Keep this." in content
    assert "## Other" in content
    assert not any(line.strip() == "## graphify" for line in content.splitlines())


def test_uninstall_project_removes_project_skill_only(tmp_path, monkeypatch):
    from graphify.__main__ import main

    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()
    user_skill = home / ".codex" / "skills" / "graphify" / "SKILL.md"
    user_skill.parent.mkdir(parents=True)
    user_skill.write_text("user skill")
    monkeypatch.chdir(project)
    with patch("graphify.__main__.Path.home", return_value=home):
        monkeypatch.setattr(sys, "argv", ["graphify", "install", "--project"])
        main()
        monkeypatch.setattr(sys, "argv", ["graphify", "uninstall", "--project"])
        main()
    assert user_skill.exists()
    assert not (project / ".codex" / "skills" / "graphify" / "SKILL.md").exists()
    assert not (project / "AGENTS.md").exists()


def _cli_dispatched_commands() -> set[str]:
    import re

    from graphify import cli

    source = Path(cli.__file__).read_text(encoding="utf-8")
    names = set(re.findall(r'cmd\s*==\s*"([a-z0-9][a-z0-9-]*)"', source))
    names |= {
        m
        for group in re.findall(r"cmd\s+in\s+\(([^)]*)\)", source)
        for m in re.findall(r'"([a-z0-9][a-z0-9-]*)"', group)
    }
    return names


def test_codex_hook_command_is_a_real_cli_subcommand(tmp_path):
    from graphify.install import _install_codex_hook

    _install_codex_hook(tmp_path)
    hooks = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    entries = [
        h
        for group in hooks["hooks"]["PreToolUse"]
        for h in group["hooks"]
        if "graphify" in h.get("command", "")
    ]
    assert entries
    dispatched = _cli_dispatched_commands()
    assert "hook-check" in dispatched
    for entry in entries:
        parts = entry["command"].split()
        subcommand = parts[1] if len(parts) > 1 else ""
        assert subcommand in dispatched


def _hook_commands(text: str) -> list:
    doc = json.loads(text)
    found = []
    for groups in doc.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                if "command" in hook:
                    found.append(hook["command"])
    return found


def test_project_install_hook_command_is_portable(tmp_path, monkeypatch):
    from graphify.__main__ import main

    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setattr("shutil.which", lambda _name: r"C:\Users\installer\graphify.EXE")
    with patch("graphify.__main__.Path.home", return_value=home):
        with patch("sys.argv", ["graphify", "install", "--project"]):
            main()
    commands = _hook_commands((project / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    assert commands
    for command in commands:
        assert command.startswith("graphify ")
        assert ":" not in command
        assert "\\" not in command
        assert ".exe" not in command.lower()


def test_user_profile_codex_install_still_resolves_absolute_path(tmp_path, monkeypatch):
    from graphify.__main__ import main

    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setattr("shutil.which", lambda _name: r"C:\Users\installer\graphify.EXE")
    with patch("graphify.__main__.Path.home", return_value=home):
        with patch("sys.argv", ["graphify", "codex", "install"]):
            main()
    commands = _hook_commands((project / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    assert commands
    for command in commands:
        assert command.startswith("C:/Users/installer/graphify.EXE ")


def test_project_install_is_idempotent(tmp_path, monkeypatch):
    from graphify.__main__ import main

    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setattr("shutil.which", lambda _name: r"C:\Users\installer\graphify.EXE")
    target = project / ".codex" / "hooks.json"

    with patch("graphify.__main__.Path.home", return_value=home):
        with patch("sys.argv", ["graphify", "install", "--project"]):
            main()
        first = target.read_text(encoding="utf-8")
        with patch("sys.argv", ["graphify", "install", "--project"]):
            main()
    assert target.read_text(encoding="utf-8") == first
