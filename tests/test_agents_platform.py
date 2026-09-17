"""Tests for the generic `agents` platform and its `skills` alias (#1432).

`graphify install --platform agents` (and the friendly `--platform skills`
alias) installs the skill to the cross-framework Agent-Skills locations: the
spec's user-global ``~/.agents/skills`` and project ``./.agents/skills`` — the
directories ``npx skills`` and spec-compliant frameworks read.

The bare ``graphify install`` behaviour is Codex-only in this Dreamliner fork.
Library ``install(platform="agents")`` still writes the generic Agent-Skills
location. The ``graphify agents install`` CLI subcommand is gated.
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import graphify.__main__ as mainmod


# --- destination map -----------------------------------------------------------


def test_agents_user_destination_is_user_global_dot_agents(tmp_path):
    """Global agents skill lands at ~/.agents/skills (the spec's user-global dir),
    NOT amp's ~/.config/agents/skills."""
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        dst = mainmod._platform_skill_destination("agents", project=False)
    assert dst == tmp_path / ".agents" / "skills" / "graphify" / "SKILL.md"


def test_agents_project_destination_is_dot_agents(tmp_path):
    """Project agents skill lands at ./.agents/skills."""
    dst = mainmod._platform_skill_destination("agents", project=True, project_dir=tmp_path)
    assert dst == tmp_path / ".agents" / "skills" / "graphify" / "SKILL.md"


# --- the skills alias ----------------------------------------------------------


def test_skills_alias_resolves_to_agents():
    assert mainmod._canonical_platform("skills") == "agents"
    assert mainmod._canonical_platform("agents") == "agents"
    # A non-aliased platform is returned unchanged.
    assert mainmod._canonical_platform("amp") == "amp"


# --- end-to-end install / uninstall via the CLI --------------------------------


def _run(tmp_path, argv, home):
    """Drive main() with argv, cwd at tmp_path, and Path.home redirected."""
    old_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        with patch.object(sys, "argv", ["graphify", *argv]):
            with patch("graphify.__main__.Path.home", return_value=home):
                mainmod.main()
    finally:
        os.chdir(old_cwd)


def _lib_install(cwd, home, platform, *, project=False):
    """Library install — CLI `--platform` is Codex-gated in this fork."""
    old = os.getcwd()
    try:
        os.chdir(cwd)
        with patch("graphify.install.Path.home", return_value=home):
            if project:
                mainmod._project_install(platform, cwd)
            else:
                mainmod.install(platform=platform)
    finally:
        os.chdir(old)


@pytest.mark.parametrize("platform_arg", ["agents", "skills"])
def test_cli_install_platform_agents_is_gated(tmp_path, platform_arg, capsys):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    with pytest.raises(SystemExit) as exc:
        _run(cwd, ["install", "--platform", platform_arg], home)
    assert exc.value.code == 2
    assert "Dreamliner is Codex-only" in capsys.readouterr().err


@pytest.mark.parametrize("platform_arg", ["agents", "skills"])
def test_install_platform_agents_writes_user_global_skill_only(tmp_path, platform_arg):
    """Library `install(platform=agents|skills)` writes ~/.agents/skills/...
    SKILL.md (+ references) and nothing else — no AGENTS.md (skill-only, like
    `--platform amp`)."""
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()

    _lib_install(cwd, home, platform_arg)

    skill = home / ".agents" / "skills" / "graphify" / "SKILL.md"
    assert skill.exists()
    assert (skill.parent / ".graphify_version").read_text() == mainmod.__version__
    assert (skill.parent / "references" / "extraction-spec.md").exists()
    # Skill-only: the --platform path must not write an AGENTS.md.
    assert not (cwd / "AGENTS.md").exists()


def test_uninstall_platform_agents_removes_user_global_skill(tmp_path):
    """Bare `graphify uninstall` clears the ~/.agents/skills skill the AGENTS.md and
    amp cleanups never reach."""
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()

    _lib_install(cwd, home, "agents")
    skill = home / ".agents" / "skills" / "graphify" / "SKILL.md"
    assert skill.exists()

    _run(cwd, ["uninstall"], home)
    assert not skill.exists()
    # The now-empty skill tree is walked away.
    assert not (home / ".agents" / "skills").exists()


@pytest.mark.parametrize("platform_arg", ["agents", "skills"])
def test_uninstall_platform_flag_global_removes_skill(tmp_path, platform_arg):
    """`graphify uninstall --platform agents|skills` (global) clears ~/.agents/skills.

    The global uninstall dispatch ignores the selected platform and always runs
    uninstall_all; this locks in that the CLI form is accepted and that
    uninstall_all's `_remove_skill_file("agents")` reaches the skill.
    """
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()

    _lib_install(cwd, home, platform_arg)
    skill = home / ".agents" / "skills" / "graphify" / "SKILL.md"
    assert skill.exists()

    _run(cwd, ["uninstall", "--platform", platform_arg], home)
    assert not skill.exists()


def test_project_uninstall_all_removes_agents_skill(tmp_path):
    """`graphify uninstall --project` (no platform) removes the agents project skill
    via the _PLATFORM_CONFIG loop — cleanly, despite agents/amp/antigravity sharing
    the ./.agents/skills path (the loop hits an already-removed tree harmlessly)."""
    home = tmp_path / "home"
    proj = tmp_path / "proj"
    home.mkdir()
    proj.mkdir()

    _lib_install(proj, home, "agents", project=True)
    project_skill = proj / ".agents" / "skills" / "graphify" / "SKILL.md"
    assert project_skill.exists()

    _run(proj, ["uninstall", "--project"], home)
    assert not project_skill.exists()


def test_install_platform_agents_project_writes_dot_agents(tmp_path):
    """Library project install for agents writes ./.agents/skills and
    leaves user scope untouched."""
    home = tmp_path / "home"
    proj = tmp_path / "proj"
    home.mkdir()
    proj.mkdir()

    _lib_install(proj, home, "agents", project=True)

    project_skill = proj / ".agents" / "skills" / "graphify" / "SKILL.md"
    assert project_skill.exists()
    assert (project_skill.parent / "references" / "extraction-spec.md").exists()
    # User scope was not touched.
    assert not (home / ".agents" / "skills").exists()

    _run(proj, ["uninstall", "--project", "--platform", "agents"], home)
    assert not project_skill.exists()


# --- the amp-twin subcommand (graphify agents install) -------------------------


def test_agents_subcommand_is_gated(tmp_path, capsys):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    with pytest.raises(SystemExit) as exc:
        _run(cwd, ["agents", "install"], home)
    assert exc.value.code == 2
    assert "Dreamliner is Codex-only" in capsys.readouterr().err


def test_agents_library_install_also_wires_agents_md(tmp_path):
    """Library `_agents_platform_install` still writes skill + AGENTS.md."""
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()

    old = os.getcwd()
    try:
        os.chdir(cwd)
        with patch("graphify.install.Path.home", return_value=home):
            mainmod._agents_platform_install(cwd)
    finally:
        os.chdir(old)

    skill = home / ".agents" / "skills" / "graphify" / "SKILL.md"
    agents_md = cwd / "AGENTS.md"
    assert skill.exists()
    assert agents_md.exists()
    assert "## graphify" in agents_md.read_text(encoding="utf-8")


def test_agents_library_install_is_idempotent(tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()

    old = os.getcwd()
    try:
        os.chdir(cwd)
        with patch("graphify.install.Path.home", return_value=home):
            mainmod._agents_platform_install(cwd)
            mainmod._agents_platform_install(cwd)
    finally:
        os.chdir(old)

    body = (cwd / "AGENTS.md").read_text(encoding="utf-8")
    assert body.count("## graphify") == 1, "AGENTS.md gained a duplicate graphify section"


# --- bare install is Codex-only -------------------------------------------------


def test_bare_install_does_not_touch_dot_agents(tmp_path):
    """`graphify install` (no platform) is Codex-only and never populates
    ~/.agents/skills (the #1432 out-of-scope guarantee)."""
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()

    _run(cwd, ["install"], home)
    assert not (home / ".agents" / "skills").exists()
    assert (home / ".codex" / "skills" / "graphify" / "SKILL.md").exists()
